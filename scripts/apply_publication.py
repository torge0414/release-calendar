"""Apply candidates/publish.json atomically to the three public calendars.

The manifest contains complete entries, not model-generated rewrites of the public
JSON files. Movie posters move from candidates/posters/ only after the complete
result passes check_data.validate() in an isolated staging directory.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from datetime import date
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import check_data

ROOT = Path(__file__).resolve().parents[1]
SPECS = {
    "games": {"file": "releases.json", "key": "games", "id": "title"},
    "movies": {"file": "movies.json", "key": "movies", "id": "sid"},
    "albums": {"file": "albums.json", "key": "albums", "id": "apple_id"},
}


class PublicationError(ValueError):
    """The manifest or resulting publication is invalid."""


@dataclass(frozen=True)
class Result:
    changed: bool
    json_files: int
    posters: int


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PublicationError(f"missing JSON file: {path}") from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PublicationError(f"invalid JSON in {path}: {exc}") from exc


def identity(kind: str, item: dict) -> str:
    field = SPECS[kind]["id"]
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PublicationError(f"{kind} upsert requires a non-empty string {field}")
    value = value.strip()
    if kind in ("movies", "albums") and not value.isdigit():
        raise PublicationError(f"{kind} ID must be numeric: {value!r}")
    return value


def parse_manifest(manifest) -> dict[str, dict[str, list]]:
    if not isinstance(manifest, dict) or type(manifest.get("version")) is not int or manifest["version"] != 1:
        raise PublicationError("manifest version must be integer 1")
    unknown = set(manifest) - {"version", *SPECS}
    if unknown:
        raise PublicationError(f"unknown manifest section(s): {', '.join(sorted(unknown))}")
    parsed = {}
    for kind in SPECS:
        section = manifest.get(kind, {})
        if not isinstance(section, dict) or set(section) - {"upsert", "remove"}:
            raise PublicationError(f"{kind} section only supports upsert and remove lists")
        upsert = section.get("upsert", [])
        remove = section.get("remove", [])
        if not isinstance(upsert, list) or not all(isinstance(item, dict) for item in upsert):
            raise PublicationError(f"{kind}.upsert must be a list of complete entry objects")
        if not isinstance(remove, list) or not all(isinstance(value, str) and value.strip() for value in remove):
            raise PublicationError(f"{kind}.remove must be a list of identity strings")
        upsert_ids = [identity(kind, item) for item in upsert]
        remove_ids = [value.strip() for value in remove]
        if kind in ("movies", "albums") and any(not value.isdigit() for value in remove_ids):
            raise PublicationError(f"{kind}.remove IDs must be numeric")
        if len(set(upsert_ids)) != len(upsert_ids) or len(set(remove_ids)) != len(remove_ids):
            raise PublicationError(f"{kind} manifest contains duplicate IDs")
        overlap = set(upsert_ids) & set(remove_ids)
        if overlap:
            raise PublicationError(f"{kind} ID cannot be both removed and upserted: {sorted(overlap)[0]}")
        parsed[kind] = {"upsert": upsert, "remove": remove_ids}
    return parsed


def public_path(root: Path, relative: str) -> Path:
    """Resolve a data image reference without permitting paths outside root."""
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise PublicationError(f"image path escapes repository: {relative}") from exc
    return path


def validate_result(root: Path, datasets: dict, posters: list[tuple[Path, Path]]) -> None:
    """Validate all JSON and local image references without modifying root."""
    with tempfile.TemporaryDirectory(prefix="validate-publication-") as folder:
        stage = Path(folder)
        for spec in SPECS.values():
            (stage / spec["file"]).write_text(
                json.dumps(datasets[spec["file"]], ensure_ascii=False), encoding="utf-8"
            )
        staged = set()
        for source, target in posters:
            relative = target.relative_to(root)
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            staged.add(relative.as_posix())
        for spec in SPECS.values():
            data = datasets[spec["file"]]
            field = {"games": "cover_img", "movies": "poster", "albums": "art"}[spec["key"]]
            for group in data["groups"]:
                for item in group[spec["key"]]:
                    relative = item.get(field)
                    if not relative or relative.startswith("https://") or relative in staged:
                        continue
                    source = public_path(root, relative)
                    destination = stage / source.relative_to(root)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
        errors = check_data.validate(stage, False)
        if errors:
            raise PublicationError("result failed calendar validation: " + "; ".join(errors))


def atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + ".publish-tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def cleared_manifest() -> str:
    return json.dumps(
        {"version": 1, **{kind: {"upsert": [], "remove": []} for kind in SPECS}},
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def apply(root: Path = ROOT, manifest_path: Path | None = None, clear_manifest: bool = False) -> Result:
    root = root.resolve()
    manifest_path = manifest_path or root / "candidates" / "publish.json"
    operations = parse_manifest(read_json(manifest_path))

    original = {kind: read_json(root / spec["file"]) for kind, spec in SPECS.items()}
    existing_errors = check_data.validate(root, False)
    if existing_errors:
        raise PublicationError("existing calendar is invalid: " + "; ".join(existing_errors))

    datasets = {spec["file"]: copy.deepcopy(original[kind]) for kind, spec in SPECS.items()}
    months = [(group["year"], group["month"]) for group in original["games"]["groups"]]
    posters: list[tuple[Path, Path]] = []

    for kind, spec in SPECS.items():
        data = datasets[spec["file"]]
        items = {}
        for group in original[kind]["groups"]:
            for item in group[spec["key"]]:
                item_id = identity(kind, item)
                if item_id in items:
                    raise PublicationError(f"{kind} contains duplicate existing ID: {item_id}")
                items[item_id] = item
        for item_id in operations[kind]["remove"]:
            items.pop(item_id, None)  # Removing an absent entry is intentionally idempotent.
        for entry in operations[kind]["upsert"]:
            item = copy.deepcopy(entry)
            item_id = identity(kind, item)
            try:
                released = date.fromisoformat(item["date"])
            except (KeyError, TypeError, ValueError) as exc:
                raise PublicationError(f"{kind} {item_id}: invalid release date") from exc
            if (released.year, released.month) not in months:
                raise PublicationError(f"{kind} {item_id}: date is outside the current three-month window")
            if (item.get("year"), item.get("month"), item.get("day")) != (
                released.year, released.month, released.day
            ):
                raise PublicationError(f"{kind} {item_id}: date fields disagree")
            items[item_id] = item
            if kind == "movies":
                expected = f"img/movie_{item_id}.jpg"
                if item.get("poster") != expected:
                    raise PublicationError(f"movie {item_id}: poster must be {expected}")
                source = root / "candidates" / "posters" / f"movie_{item_id}.jpg"
                target = root / expected
                if target.exists() and not target.is_file():
                    raise PublicationError(f"movie {item_id}: poster target is not a file")
                if not target.exists():
                    if not source.is_file():
                        raise PublicationError(f"movie {item_id}: missing candidate poster {source.relative_to(root)}")
                    with source.open("rb") as stream:
                        if not stream.read(3) == b"\xff\xd8\xff":
                            raise PublicationError(f"movie {item_id}: candidate poster is not a JPEG")
                    posters.append((source, target))

        groups = copy.deepcopy(original[kind]["groups"])
        by_month = {(group["year"], group["month"]): group for group in groups}
        for group in groups:
            group[spec["key"]] = []
        for item in items.values():
            released = date.fromisoformat(item["date"])
            by_month[(released.year, released.month)][spec["key"]].append(item)
        for group in groups:
            group[spec["key"]].sort(key=lambda item: item["date"])
        data["groups"] = groups

    validate_result(root, datasets, posters)
    changed_data = {
        kind: datasets[spec["file"]] != original[kind]
        for kind, spec in SPECS.items()
    }
    empty_manifest = cleared_manifest()
    manifest_changed = clear_manifest and manifest_path.read_text(encoding="utf-8") != empty_manifest
    if not any(changed_data.values()) and not posters and not manifest_changed:
        return Result(False, 0, 0)

    snapshots = {
        root / SPECS[kind]["file"]: (root / SPECS[kind]["file"]).read_bytes()
        for kind, changed in changed_data.items() if changed
    }
    if manifest_changed:
        snapshots[manifest_path] = manifest_path.read_bytes()
    moved = []
    try:
        for source, target in posters:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
            moved.append((source, target))
        for kind, changed in changed_data.items():
            if changed:
                spec = SPECS[kind]
                atomic_write(root / spec["file"], json.dumps(datasets[spec["file"]], ensure_ascii=False))
        if manifest_changed:
            atomic_write(manifest_path, empty_manifest)
    except Exception:
        for path, content in snapshots.items():
            atomic_write(path, content.decode("utf-8"))
        for source, target in reversed(moved):
            if target.exists():
                target.rename(source)
        raise

    errors = check_data.validate(root, False)
    if errors:  # The staging check above should make this unreachable.
        raise PublicationError("post-write validation failed: " + "; ".join(errors))
    return Result(True, sum(changed_data.values()), len(posters))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--keep-manifest", action="store_true", help="keep operations for an explicit idempotency check")
    args = parser.parse_args()
    try:
        # The CLI consumes successful operations so a later run cannot restore stale scores.
        result = apply(args.root, args.manifest, clear_manifest=not args.keep_manifest)
    except PublicationError as exc:
        print(f"Publication rejected: {exc}", file=sys.stderr)
        return 1
    if result.changed:
        print(f"Publication applied: {result.json_files} JSON file(s), {result.posters} poster(s) moved")
    else:
        print("Publication already applied; no changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
