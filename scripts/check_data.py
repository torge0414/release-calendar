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
    albums_data = json.loads((root / "albums.json").read_text(encoding="utf-8"))
    game_months = [(g.get("year"), g.get("month")) for g in games_data.get("groups", [])]
    movie_months = [(g.get("year"), g.get("month")) for g in movies_data.get("groups", [])]
    album_months = [(g.get("year"), g.get("month")) for g in albums_data.get("groups", [])]
    if game_months != movie_months:
        fail(errors, "game/movie month groups disagree")
    if game_months != album_months:
        fail(errors, "game/album month groups disagree")
    image_jobs = []
    for kind, data, list_key in (
        ("game", games_data, "games"),
        ("movie", movies_data, "movies"),
        ("album", albums_data, "albums"),
    ):
        groups = data.get("groups")
        if not isinstance(groups, list) or len(groups) != 3:
            fail(errors, f"{kind}: expected exactly three month groups")
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
                identity = {"movie": item.get("sid"), "album": (item.get("artist"), title)}.get(kind, title)
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
                    cover = item.get("cover_img")
                    if cover and not cover.startswith("https://") and not (root / cover).is_file():
                        fail(errors, f"{label}: missing local cover {cover}")
                elif kind == "album":
                    # 2026-10-15 起音乐不显示评分，也不存评分字段
                    if not isinstance(item.get("artist"), str) or not item["artist"].strip():
                        fail(errors, f"{label}: empty artist")
                    if "mc" in item or "mc_url" in item:
                        fail(errors, f"{label}: music entries no longer carry scores")
                    apple = item.get("apple_url")
                    if apple and not str(apple).startswith("https://music.apple.com/"):
                        fail(errors, f"{label}: invalid Apple Music URL")
                    art = item.get("art")
                    if art and not art.startswith("https://"):
                        if not (root / art).is_file():
                            fail(errors, f"{label}: missing local cover {art}")
                    elif art:
                        image_jobs.append((label, [art]))
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
        for previous, following in zip(months, months[1:]):
            next_year = previous[0] + (previous[1] == 12)
            next_month = previous[1] % 12 + 1
            if following != (next_year, next_month):
                fail(errors, f"{kind}: groups are not consecutive months")
    if check_images:
        def check_candidates(job: tuple[str, list[str]]) -> str | None:
            label, candidates = job
            for url in candidates:
                if url.startswith("https://") and check_image(url):
                    return None
                if not url.startswith("https://") and (root / url).is_file():
                    with (root / url).open("rb") as stream:
                        if stream.read(32).startswith(IMAGE_MAGIC):
                            return None
            return f"{label}: no working image candidate"
        with ThreadPoolExecutor(max_workers=5) as pool:
            errors.extend(error for error in pool.map(check_candidates, image_jobs) if error)
    return errors


def missing_title_font_chars(root: Path) -> list[str]:
    """CJK characters in titles that the bundled serif subset font does not cover."""
    chars_file = root / "fonts" / "title-serif-chars.txt"
    if not chars_file.exists():
        return []
    covered = set(chars_file.read_text(encoding="utf-8"))
    missing = set()
    for name, key in (("releases.json", "games"), ("movies.json", "movies"), ("albums.json", "albums")):
        data = json.loads((root / name).read_text(encoding="utf-8"))
        for group in data.get("groups", []):
            for item in group.get(key, []):
                for ch in str(item.get("title", "")):
                    if ("\u3000" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef") and ch not in covered:
                        missing.add(ch)
    return sorted(missing)


LOCAL_IMAGE_WARN_KB = 220


def oversized_local_images(root: Path) -> list[str]:
    """Local covers/posters that are much larger than the page needs (posters: about 600px wide)."""
    heavy = []
    for name, key, field in (
        ("releases.json", "games", "cover_img"),
        ("movies.json", "movies", "poster"),
        ("albums.json", "albums", "art"),
    ):
        data = json.loads((root / name).read_text(encoding="utf-8"))
        for group in data.get("groups", []):
            for item in group.get(key, []):
                rel = str(item.get(field) or "")
                path = root / rel
                if rel.startswith("img/") and path.exists() and path.stat().st_size > LOCAL_IMAGE_WARN_KB * 1024:
                    heavy.append(f"{rel} ({path.stat().st_size // 1024} KB)")
    return heavy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", action="store_true", help="also request external images")
    args = parser.parse_args()
    errors = validate(ROOT, args.images)
    if errors:
        for error in errors:
            print(error)
        return 1
    heavy = oversized_local_images(ROOT)
    if heavy:
        # 只提醒不报错：海报缩到约 600px 宽、JPEG 质量 80 左右即可
        print("warning: large local images, resize before committing: " + ", ".join(heavy))
    missing = missing_title_font_chars(ROOT)
    if missing:
        # 只提醒不报错：缺字会回落到系统宋体，不影响数据和每日任务
        print("warning: title font subset lacks " + "".join(missing) + "; rebuild fonts/title-serif-sc-bold.woff2 (see HANDOVER.md)")
    print("Calendar data valid" + ("; displayed image sources reachable" if args.images else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
