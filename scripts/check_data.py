"""Validate the calendar JSON and optionally test displayed image sources."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
IMAGE_MAGIC = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF87a", b"GIF89a", b"RIFF")


def check_image(url: str) -> bool:
    try:
        request = Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://torge0414.github.io/release-calendar/",
            "Range": "bytes=0-31",
        })
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            start = response.read(32)
        return content_type.startswith("image/") and start.startswith(IMAGE_MAGIC)
    except (HTTPError, URLError, TimeoutError):
        return False


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate(root: Path, check_images: bool) -> list[str]:
    errors = []
    games_data = json.loads((root / "releases.json").read_text(encoding="utf-8"))
    movies_data = json.loads((root / "movies.json").read_text(encoding="utf-8"))
    image_jobs = []
    for kind, data, list_key in (
        ("game", games_data, "games"),
        ("movie", movies_data, "movies"),
    ):
        groups = data.get("groups")
        if not isinstance(groups, list) or len(groups) != 2:
            fail(errors, f"{kind}: expected exactly two month groups")
            continue
        seen = set()
        months = []
        for group in groups:
            year, month = group.get("year"), group.get("month")
            if not isinstance(year, int) or not isinstance(month, int) or not 1 <= month <= 12:
                fail(errors, f"{kind}: invalid group year/month")
                continue
            months.append((year, month))
            items = group.get(list_key)
            if not isinstance(items, list):
                fail(errors, f"{kind} {year}-{month}: missing {list_key}")
                continue
            for item in items:
                title = item.get("title")
                label = f"{kind} {title or '<untitled>'}"
                if not isinstance(title, str) or not title.strip():
                    fail(errors, f"{label}: empty title")
                    continue
                identity = item.get("sid") if kind == "movie" else title
                if identity in seen:
                    fail(errors, f"{label}: duplicate entry")
                seen.add(identity)
                try:
                    release = date.fromisoformat(item["date"])
                    if (release.year, release.month, release.day) != (
                        item.get("year"), item.get("month"), item.get("day")
                    ):
                        fail(errors, f"{label}: date fields disagree")
                    if (release.year, release.month) != (year, month):
                        fail(errors, f"{label}: wrong month group")
                except (KeyError, TypeError, ValueError):
                    fail(errors, f"{label}: invalid release date")
                if kind == "game":
                    score = item.get("mc")
                    if score is not None and (not isinstance(score, int) or not 0 <= score <= 100):
                        fail(errors, f"{label}: invalid Metacritic score")
                    platforms = item.get("plats")
                    if not isinstance(platforms, list) or not platforms:
                        fail(errors, f"{label}: no platforms")
                    else:
                        for platform in platforms:
                            if platform.get("key") not in ("steam", "ps", "ns"):
                                fail(errors, f"{label}: unknown platform")
                            if not str(platform.get("url") or "").startswith("https://"):
                                fail(errors, f"{label}: invalid platform URL")
                    candidates = [item.get("cover_img")] if item.get("cover_img") else []
                    candidates += [p.get("img") for p in (platforms or []) if p.get("img")]
                    if candidates:
                        image_jobs.append((label, candidates))
                else:
                    score = item.get("score")
                    votes = item.get("votes")
                    if score is not None and (not isinstance(score, (int, float)) or not 0 <= score <= 10):
                        fail(errors, f"{label}: invalid Douban score")
                    if not isinstance(votes, int) or votes < 0:
                        fail(errors, f"{label}: invalid vote count")
                    if str(item.get("sid") or "") not in str(item.get("url") or ""):
                        fail(errors, f"{label}: Douban subject ID and URL disagree")
                    poster = item.get("poster")
                    if poster and not poster.startswith("https://"):
                        if not (root / poster).is_file():
                            fail(errors, f"{label}: missing local poster {poster}")
                    elif poster:
                        image_jobs.append((label, [poster]))
        if len(months) == 2:
            next_year = months[0][0] + (months[0][1] == 12)
            next_month = months[0][1] % 12 + 1
            if months[1] != (next_year, next_month):
                fail(errors, f"{kind}: groups are not consecutive months")
    if check_images:
        def check_candidates(job: tuple[str, list[str]]) -> str | None:
            label, candidates = job
            for url in candidates:
                if url.startswith("https://") and check_image(url):
                    return None
            return f"{label}: no working image candidate"
        with ThreadPoolExecutor(max_workers=5) as pool:
            errors.extend(error for error in pool.map(check_candidates, image_jobs) if error)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", action="store_true", help="also request external images")
    args = parser.parse_args()
    errors = validate(ROOT, args.images)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Calendar data valid" + ("; displayed image sources reachable" if args.images else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
