"""Refresh scores and Steam prices without changing the monthly selection."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
METASCORE = re.compile(
    r'aria-label="Metascore\s+(\d+)\s+out of 100"[^>]*'
    r'data-testid="global-score-value-wrapper"',
    re.IGNORECASE,
)
TIMEOUT = 25


def fetch(url: str, headers: dict[str, str]) -> str:
    with urlopen(Request(url, headers=headers), timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def game_score(item: dict) -> tuple[str, int | None]:
    url = item.get("mc_url")
    if not url:
        return ("no_url", None)
    try:
        page = fetch(url, {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })
        match = METASCORE.search(page)
        if not match:
            return ("unrated", None)
        score = int(match.group(1))
        if not 0 <= score <= 100:
            raise ValueError("Metacritic score outside 0–100")
        return ("ok", score)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        return (f"error: {exc}", None)


def movie_score(item: dict) -> tuple[str, tuple[float | None, int | None] | None]:
    sid = str(item.get("sid") or "").strip()
    if not sid:
        return ("no_sid", None)
    url = f"https://m.douban.com/rexxar/api/v2/movie/{sid}?ck=&for_mobile=1"
    try:
        page = fetch(url, {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
            "Referer": f"https://m.douban.com/movie/subject/{sid}/",
            "Accept": "application/json",
        })
        payload = json.loads(page)
        if str(payload.get("id")) != sid:
            raise ValueError("Douban subject ID mismatch")
        rating = payload.get("rating") or {}
        raw_value, raw_count = rating.get("value"), rating.get("count")
        value = float(raw_value) if raw_value not in (None, "") else None
        count = int(raw_count) if raw_count not in (None, "") else None
        if value is not None and not 0 <= value <= 10:
            raise ValueError("Douban score outside 0–10")
        if count is not None and count < 0:
            raise ValueError("negative Douban vote count")
        return ("ok", (value, count))
    except (HTTPError, URLError, TimeoutError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return (f"error: {exc}", None)


def steam_price(item: dict) -> tuple[str, float | None]:
    url = item.get("steam_url") or ""
    match = re.fullmatch(r"https?://store\.steampowered\.com/app/(\d+)/?", url)
    if not match:
        return ("no_url", None)
    app_id = match.group(1)
    api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=cn&l=schinese"
    try:
        page = fetch(api_url, {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        })
        payload = json.loads(page).get(app_id) or {}
        if not payload.get("success"):
            return ("unavailable", None)
        data = payload.get("data") or {}
        if data.get("steam_appid") != int(app_id) or data.get("type") != "game":
            raise ValueError("Steam app ID or type mismatch")
        overview = data.get("price_overview") or {}
        if overview.get("currency") != "CNY":
            return ("unavailable", None)
        final = overview.get("final")
        if isinstance(final, bool) or not isinstance(final, int) or final < 0:
            return ("unavailable", None)
        return ("ok", final / 100)
    except (HTTPError, URLError, TimeoutError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return (f"error: {exc}", None)


def write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(", ", ": ")),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="check sources but do not write files")
    args = parser.parse_args()

    game_path, movie_path = ROOT / "releases.json", ROOT / "movies.json"
    games_data = json.loads(game_path.read_text(encoding="utf-8"))
    movies_data = json.loads(movie_path.read_text(encoding="utf-8"))
    games = [entry for group in games_data["groups"] for entry in group["games"]]
    movies = [entry for group in movies_data["groups"] for entry in group["movies"]]
    jobs = [("game", item) for item in games] + [("movie", item) for item in movies]
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(
            lambda job: game_score(job[1]) if job[0] == "game" else movie_score(job[1]),
            jobs,
        ))

    total_sources = 0
    errors = []
    score_errors = []
    changes = []
    game_changed = movie_changed = False
    for (kind, item), (status, rating) in zip(jobs, results):
        if status not in ("no_url", "no_sid"):
            total_sources += 1
        if status.startswith("error:"):
            score_errors.append(f"{kind} {item['title']}: {status}")
            errors.append(score_errors[-1])
        if status != "ok":
            continue
        if kind == "game":
            if item.get("mc") != rating:
                changes.append(f"游戏 {item['title']}: {item.get('mc')} → {rating}")
                item["mc"] = rating
                game_changed = True
        else:
            value, count = rating
            if value not in (None, 0) and item.get("score") != value:
                changes.append(f"电影 {item['title']} 评分: {item.get('score')} → {value}")
                item["score"] = value
                movie_changed = True
            if count not in (None, 0) and item.get("votes") != count:
                changes.append(f"电影 {item['title']} 人数: {item.get('votes')} → {count}")
                item["votes"] = count
                movie_changed = True

    steam_games = [item for item in games if item.get("steam_url")]
    with ThreadPoolExecutor(max_workers=5) as pool:
        price_results = list(pool.map(steam_price, steam_games))
    for item, (status, price) in zip(steam_games, price_results):
        if status.startswith("error:"):
            errors.append(f"Steam {item['title']}: {status}")
        if status != "ok":
            continue
        old_price = item.get("steam_price")
        if old_price != price:
            changes.append(f"游戏 {item['title']} Steam 国区现价: {old_price} → {price}")
            item["steam_price"] = price
            game_changed = True
        for platform in item.get("plats", []):
            if platform.get("key") == "steam" and platform.get("price") != price:
                platform["price"] = price
                game_changed = True

    print(json.dumps({
        "checked": {"games": len(games), "movies": len(movies)},
        "changes": changes,
        "errors": errors,
    }, ensure_ascii=False, indent=2))
    if total_sources and len(score_errors) > total_sources // 2:
        print("More than half of score sources failed; no data written.")
        return 1
    if not args.dry_run:
        now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
        for changed, data, path in (
            (game_changed, games_data, game_path),
            (movie_changed, movies_data, movie_path),
        ):
            if changed:
                data["updated"] = now
                data["fetched_at"] = now
                write_json(path, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
