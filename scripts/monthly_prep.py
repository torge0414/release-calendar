"""Monthly preparation: roll the three-month window and collect candidate data.

Runs in GitHub Actions on the 1st and 15th of each month (00:05 Beijing), before Kimi's
curation task. It only does deterministic work and never chooses titles:

1. Roll releases.json / movies.json / albums.json to the new window
   (previous, current, next month). Groups that leave the window are dropped,
   new months start empty, existing entries are untouched.
2. Collect candidates into candidates/latest.json:
   - movies: Douban "now showing" + "coming soon" (heat: wish / rating counts),
     details for titles inside the window, and posters for titles that pass the
     heat line. TMDB posters are ranked by language and fit to the 2:3 frame.
     Missing posters and download failures are recorded with the candidates.
   - music: Apple Music US most-played albums, Metacritic coming-soon list,
     Wikipedia "List of <year> albums", Wikipedia "<year> in South Korean music",
     plus iTunes lookups (genre, track count, artwork, China storefront link).
   - games: Wikipedia "List of video games released in <year>" (date, title,
     platforms, type such as new / remaster / port, genre, developer, publisher).
Every source is optional: a failure is recorded in "errors" and the rest go on.
Standard library only except Pillow for lossless-ratio poster resizing in Actions.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import html
from html.parser import HTMLParser
from io import BytesIO
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import time
from unicodedata import normalize
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "candidates"
BJ = timezone(timedelta(hours=8))
TIMEOUT = 30
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
MOVIE_HEAT = 5000          # HANDOVER §4B：想看或评分人数
DOUBAN_DELAY = 6           # 豆瓣对同一 IP 限流（code 1309）：慢一点，触发后停 90 秒再试一次
DOUBAN_MAX_DETAILS = 40
ITUNES_DELAY = 3.2         # iTunes Search API 约每分钟 20 次
FILES = (("releases.json", "games"), ("movies.json", "movies"), ("albums.json", "albums"))


def fetch(url: str, headers: dict[str, str] | None = None, binary: bool = False):
    with urlopen(Request(url, headers={"User-Agent": UA, **(headers or {})}), timeout=TIMEOUT) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", errors="replace")


def fetch_json(url: str, headers: dict[str, str] | None = None):
    return json.loads(fetch(url, {"Accept": "application/json", **(headers or {})}))


# ---------- 1. 三个月窗口 ----------

def window_for(today: date) -> list[tuple[int, int]]:
    def shift(y: int, m: int, d: int) -> tuple[int, int]:
        n = y * 12 + (m - 1) + d
        return n // 12, n % 12 + 1
    return [shift(today.year, today.month, d) for d in (-1, 0, 1)]


def roll(data: dict, key: str, months: list[tuple[int, int]]) -> bool:
    old = data.get("groups", [])
    by_month = {(g.get("year"), g.get("month")): g for g in old}
    groups = []
    for y, m in months:
        g = by_month.get((y, m)) or {"year": y, "month": m, "label": f"{y}年{m}月", key: []}
        groups.append(g)
    changed = [(g["year"], g["month"]) for g in old] != months
    data["groups"] = groups
    return changed


# ---------- HTML 表格解析（带 rowspan） ----------

class Tables(HTMLParser):
    """Collect wikitable rows as {"section", "cells", "linked"}; rowspan cells are repeated."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.section, self.heading = [], "", None
        self.in_table = 0
        self.row = None
        self.cell = None
        self.span = {}  # column -> [remaining, text, linked]
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("h2", "h3", "h4"):
            self.heading = ""
        elif tag == "table" and "wikitable" in (a.get("class") or ""):
            self.in_table += 1
            self.span = {}
        elif self.in_table and tag == "tr":
            self.row = []
        elif self.in_table and self.row is not None and tag in ("td", "th"):
            self.cell = {"text": "", "linked": False, "rowspan": int(re.sub(r"\D", "", a.get("rowspan") or "1") or 1)}
        elif self.cell is not None and tag == "a":
            self.cell["linked"] = True
        elif self.cell is not None and tag == "br":
            self.cell["text"] += " "
        elif tag in ("sup", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("h2", "h3", "h4") and self.heading is not None:
            self.section = re.sub(r"\s*\[edit\]\s*$", "", self.heading.strip())
            self.heading = None
        elif tag in ("sup", "style") and self.skip:
            self.skip -= 1
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            cells, col, it = [], 0, iter(self.row)
            pending = list(self.row)
            while pending or any(c >= col for c in self.span):
                if col in self.span:
                    left, text, linked = self.span[col]
                    cells.append((text, linked))
                    if left <= 1:
                        del self.span[col]
                    else:
                        self.span[col] = [left - 1, text, linked]
                elif pending:
                    c = pending.pop(0)
                    text = re.sub(r"\s+", " ", c["text"]).strip()
                    cells.append((text, c["linked"]))
                    if c["rowspan"] > 1:
                        self.span[col] = [c["rowspan"] - 1, text, c["linked"]]
                else:
                    break
                col += 1
            if cells:
                self.rows.append({"section": self.section, "cells": [t for t, _ in cells], "linked": [l for _, l in cells]})
            self.row = None
        elif tag == "table" and self.in_table:
            self.in_table -= 1

    def handle_data(self, data):
        if self.skip:
            return
        if self.heading is not None:
            self.heading += data
        if self.cell is not None:
            self.cell["text"] += data


def wiki_rows(title: str) -> list[dict]:
    page = fetch("https://en.wikipedia.org/api/rest_v1/page/html/" + quote(title.replace(" ", "_")))
    parser = Tables()
    parser.feed(page)
    return parser.rows


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def month_of(section: str, cell0: str) -> int | None:
    for i, name in enumerate(MONTHS, 1):
        if section.startswith(name) or cell0.startswith(name) or cell0.startswith(name[:3] + " "):
            return i
    return None


def day_of(text: str) -> int | None:
    m = re.search(r"\b(\d{1,2})\b", text)
    return int(m.group(1)) if m else None


# ---------- 2a. 电影（豆瓣） ----------

class RateLimited(Exception):
    pass


def douban(path: str, retry: bool = True):
    time.sleep(DOUBAN_DELAY)
    try:
        return fetch_json("https://m.douban.com/rexxar/api/v2/" + path, {"User-Agent": MOBILE_UA, "Referer": "https://m.douban.com/movie/"})
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        if "1309" in body or "rate_limit" in body or exc.code == 429:
            if retry:
                time.sleep(90)
                return douban(path, retry=False)
            raise RateLimited(path) from exc
        raise


TMDB_POSTER_LIMIT = 4  # downloads per language and aspect-ratio group
MIN_POSTER_FRAME_FIT = 0.9


def poster_frame_fit(width, height) -> float:
    """Fraction of the image visible when covering the site's 2:3 frame."""
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        return 0
    scaled_width, scaled_height = width * 3, height * 2
    return min(scaled_width, scaled_height) / max(scaled_width, scaled_height)


def tmdb_api(path: str, api_key: str, **params) -> dict:
    url = f"https://api.themoviedb.org/3/{path}?" + urlencode({"api_key": api_key, **params})
    try:
        result = fetch_json(url)
    except HTTPError as exc:
        raise ValueError(f"TMDB API returned HTTP {exc.code}") from None
    except (OSError, ValueError):
        # The request URL contains the key. Never log it or the raw exception.
        raise ValueError("TMDB API connection failed or returned invalid JSON") from None
    if not isinstance(result, dict):
        raise ValueError("TMDB API returned an unexpected response")
    return result


def poster_title_key(title: str) -> str:
    return "".join(char for char in normalize("NFKC", title).casefold() if char.isalnum())


def tmdb_movie_id(candidate: dict, api_key: str) -> int:
    year = str(candidate.get("year") or "")
    if not re.fullmatch(r"\d{4}", year):
        raise ValueError("Missing original release year for TMDB match")
    titles = {}
    for title in (candidate.get("title"), candidate.get("original_title")):
        key = poster_title_key(title or "")
        if key:
            titles[key] = title
    matches = set()
    for title in titles.values():
        results = tmdb_api("search/movie", api_key, query=title, language="zh-CN",
                           primary_release_year=year)
        if (results.get("total_pages") or 0) > 1:
            raise ValueError("TMDB title and year search returned more than one page")
        for movie in results.get("results") or []:
            if (str(movie.get("release_date") or "")[:4] == year
                    and type(movie.get("id")) is int
                    and any(poster_title_key(movie.get(field) or "") in titles
                            for field in ("title", "original_title"))):
                matches.add(movie["id"])
    if len(matches) != 1:
        reason = "No" if not matches else "More than one"
        raise ValueError(f"{reason} exact TMDB title and year match")
    return matches.pop()


def tmdb_poster_options(posters: list[dict]):
    groups = {("zh", True): [], ("zh", False): [], ("en", True): [], ("en", False): []}
    for poster in posters:
        fit = poster_frame_fit(poster.get("width"), poster.get("height"))
        group = (poster.get("iso_639_1"), fit == 1)
        if (group in groups and fit >= MIN_POSTER_FRAME_FIT
                and re.fullmatch(r"/[A-Za-z0-9]+\.jpg", poster.get("file_path") or "")):
            groups[group].append((fit, poster))
    for group in groups.values():
        ranked = sorted(group, key=lambda option: option[0], reverse=True)
        for _, poster in ranked[:TMDB_POSTER_LIMIT]:
            yield poster


def tmdb_candidate_poster(candidate: dict, target: Path, api_key: str) -> dict:
    from PIL import Image

    movie_id = tmdb_movie_id(candidate, api_key)
    gallery = {"tmdb_id": movie_id, "page_url": f"https://www.themoviedb.org/movie/{movie_id}/images/posters"}
    images = tmdb_api(f"movie/{movie_id}/images", api_key, include_image_language="zh,en")
    failures = []
    for poster in tmdb_poster_options(images.get("posters") or []):
        path = poster["file_path"]
        image_url = f"https://image.tmdb.org/t/p/original{path}"
        try:
            data = fetch(image_url, binary=True)
            with Image.open(BytesIO(data)) as image:
                width, height = image.size
                if (width, height) != (poster["width"], poster["height"]):
                    failures.append(f"{path}: downloaded dimensions differ from TMDB metadata")
                    continue
                output_size = (600, round(height * 600 / width))
                output = BytesIO()
                image.convert("RGB").resize(output_size, Image.Resampling.LANCZOS).save(output, "JPEG", quality=80, optimize=True)
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            failures.append(f"{path}: {exc}")
            continue
        target.write_bytes(output.getvalue())
        return {**gallery, "status": "ready", "image_url": image_url, "language": poster["iso_639_1"],
                "original_width": width, "original_height": height, "width": output_size[0], "height": output_size[1],
                "download_failures": failures}
    reason = ("Could not download a usable TMDB poster" if failures
              else "No Chinese- or English-language TMDB poster fits the 2:3 frame")
    return {**gallery, "status": "unavailable", "reason": reason, "download_failures": failures}


def collect_movies(months, errors) -> list[dict]:
    items = {}
    for coll in ("movie_soon", "movie_showing"):  # 即将上映优先：限流时先保住待映片的详情
        try:
            for x in douban(f"subject_collection/{coll}/items?start=0&count=60").get("subject_collection_items", []):
                r = x.get("rating") or {}
                items[str(x["id"])] = {"sid": str(x["id"]), "title": x.get("title"), "list": coll,
                                       "release_hint": x.get("release_date"), "wish": x.get("wish_count"),
                                       "score": r.get("value"), "votes": r.get("count")}
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
            errors.append(f"douban {coll}: {exc}")
    window = {(y, m) for y, m in months}
    out, limited = [], False
    for sid, it in items.items():
        out.append(it)
        # 「正在上映」里有不少老片重映，列表给的日期（MM.DD）不在窗口月份内的直接跳过详情
        hint = re.match(r"(\d{2})\.(\d{2})", str(it.get("release_hint") or ""))
        if it["list"] == "movie_showing" and hint and int(hint.group(1)) not in {m for _, m in months}:
            it["skipped"] = "release month outside window"
            continue
        if limited or sum(1 for x in out if "pubdate" in x) >= DOUBAN_MAX_DETAILS:
            it["skipped"] = "douban rate limit / detail cap"
            continue
        try:
            j = douban(f"movie/{sid}?ck=&for_mobile=1")
        except RateLimited:
            errors.append(f"douban rate limited at movie {sid}; remaining details skipped")
            limited, it["skipped"] = True, "douban rate limit"
            continue
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            errors.append(f"douban movie {sid}: {exc}")
            continue
        pub = ";".join(j.get("pubdate") or [])
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})\(中国大陆\)", pub)
        mainland = date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
        r = j.get("rating") or {}
        it.update({"pubdate": pub, "mainland_date": mainland.isoformat() if mainland else None,
                   "year": j.get("year"), "original_title": j.get("original_title"), "aka": j.get("aka") or [],
                   "genres": j.get("genres"), "countries": j.get("countries"),
                   "directors": [d.get("name") for d in j.get("directors") or []],
                   "actors": [a.get("name") for a in (j.get("actors") or [])[:3]],
                   "score": r.get("value"), "votes": r.get("count"), "comments": j.get("comment_count"),
                   "null_rating_reason": j.get("null_rating_reason")})
        it["in_window"] = bool(mainland and (mainland.year, mainland.month) in window)
    for it in out:
        it["heat_ok"] = max(it.get("wish") or 0, it.get("votes") or 0) >= MOVIE_HEAT
    # 新候选海报统一从 TMDB 下载，缺图的原因保留在候选数据中。
    api_key = os.environ.get("TMDB_API_KEY", "").strip()
    (CAND / "posters").mkdir(parents=True, exist_ok=True)
    for it in out:
        if not (it.get("in_window") and it["heat_ok"]):
            continue
        target = CAND / "posters" / f"movie_{it['sid']}.jpg"
        if (ROOT / "img" / target.name).exists():
            it["poster_file"] = f"img/{target.name}"
            it["poster_source"] = "existing"
            continue
        try:
            if not api_key:
                raise ValueError("TMDB_API_KEY is not configured")
            meta = tmdb_candidate_poster(it, target, api_key)
        except (ValueError, ImportError, OSError) as exc:
            meta = {"status": "unavailable", "reason": str(exc)}
        it["poster_gallery"] = meta
        if meta["status"] == "ready":
            it["poster_file"] = f"candidates/posters/{target.name}"
            it["poster_source"] = "tmdb"
            continue
        errors.append(f"TMDB poster {it['sid']}: {meta['reason']}")
    return out


# ---------- 2b. 音乐 ----------

def itunes(path: str):
    time.sleep(ITUNES_DELAY)
    return fetch_json("https://itunes.apple.com/" + path)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", html.unescape(s or "").lower().replace("&", "and"))


def itunes_match(artist: str, title: str, errors) -> dict | None:
    try:
        res = itunes(f"search?term={quote(artist + ' ' + title)}&entity=album&country=us&limit=10").get("results", [])
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        errors.append(f"itunes {artist} - {title}: {exc}")
        return None
    t = norm(title)[:8]
    best = next((x for x in res if t and t in norm(x.get("collectionName")) and "single" not in x.get("collectionName", "").lower()), None)
    if not best:
        return None
    info = {k: best.get(k) for k in ("collectionId", "artistName", "collectionName", "releaseDate", "trackCount",
                                       "primaryGenreName", "collectionExplicitness")}
    info["art"] = (best.get("artworkUrl100") or "").replace("100x100bb", "600x600bb")
    try:
        cn = itunes(f"lookup?id={best['collectionId']}&country=cn").get("results", [])
        info["cn_url"] = cn[0]["collectionViewUrl"].split("?")[0] if cn else None
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        errors.append(f"itunes cn {best.get('collectionId')}: {exc}")
    return info


def collect_music(months, errors) -> dict:
    window = {(y, m) for y, m in months}
    upcoming = set(months[1:])  # 上月沿用已发布名单，只给本月和下月查 iTunes
    out = {"apple_top": [], "metacritic_soon": [], "wikipedia": [], "kpop": []}
    try:
        feed = fetch_json("https://rss.marketingtools.apple.com/api/v2/us/music/most-played/100/albums.json")
        for x in feed["feed"]["results"]:
            d = x.get("releaseDate") or ""
            if d[:7] and (int(d[:4]), int(d[5:7])) in window:
                out["apple_top"].append({"date": d, "artist": x.get("artistName"), "title": x.get("name"), "id": x.get("id")})
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        errors.append(f"apple rss: {exc}")
    try:
        page = fetch("https://www.metacritic.com/browse/albums/release-date/coming-soon/date")
        current = None
        for m in re.finditer(r'<th class="head[^"]*"[^>]*>\s*([^<]+?)\s*</th>|<td class="artistName">(.*?)</td>\s*<td class="albumTitle">(.*?)</td>\s*<td class="dataComment">(.*?)</td>', page, re.S):
            if m.group(1):
                current = m.group(1).strip()
            else:
                clean = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).strip()
                out["metacritic_soon"].append({"date": current, "artist": clean(m.group(2)), "title": clean(m.group(3)), "note": clean(m.group(4))})
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        errors.append(f"metacritic coming soon: {exc}")
    for year in sorted({y for y, _ in months}):
        try:
            # 2026-11 起 Wikipedia 把年度专辑列表拆成上下半年两个子页面，主页面只剩链接
            rows = []
            for part in (f"List of {year} albums (January–June)", f"List of {year} albums (July–December)"):
                try:
                    rows += wiki_rows(part)
                except HTTPError as exc:
                    if exc.code != 404:
                        raise
            if not rows:
                rows = wiki_rows(f"List of {year} albums")
            if not rows:
                errors.append(f"wikipedia albums {year}: no table rows parsed")
            for r in rows:
                c = r["cells"]
                if len(c) < 4 or c[1] in ("Artist", "Artist(s)"):
                    continue
                month = month_of(r["section"], c[0])
                if not month or (year, month) not in window:
                    continue
                out["wikipedia"].append({"year": year, "month": month, "day": day_of(c[0]), "artist": c[1], "title": c[2],
                                         "genre": c[3] if len(c) > 4 else "", "label": c[4] if len(c) > 4 else c[3],
                                         "album_has_article": bool(r["linked"][2])})
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            errors.append(f"wikipedia albums {year}: {exc}")
        try:
            for r in wiki_rows(f"{year} in South Korean music"):
                c = r["cells"]
                month = month_of(r["section"], "")
                if len(c) < 3 or c[1] == "Album" or not month or (year, month) not in window:
                    continue
                out["kpop"].append({"year": year, "month": month, "day": day_of(c[0]), "title": c[1], "artist": c[2]})
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            errors.append(f"wikipedia kpop {year}: {exc}")
    # 本月和下月的候选查一次 iTunes（日期、流派、曲目数、封面、国区链接）
    seen = set()
    for src in ("apple_top", "metacritic_soon", "wikipedia", "kpop"):
        for it in out[src]:
            ym = (it["year"], it["month"]) if "month" in it else None
            if src == "apple_top":
                ym = (int(it["date"][:4]), int(it["date"][5:7]))
            if ym is not None and ym not in upcoming:
                continue
            key = norm(it["artist"]) + "|" + norm(it["title"])
            if key in seen:
                continue
            seen.add(key)
            it["itunes"] = itunes_match(it["artist"], it["title"], errors)
    return out


# ---------- 2c. 游戏 ----------

def collect_games(months, errors) -> list[dict]:
    window = {(y, m) for y, m in months}
    out = []
    for year in sorted({y for y, _ in months}):
        try:
            for r in wiki_rows(f"List of video games released in {year}"):
                c = r["cells"]
                if len(c) < 7 or c[1] == "Title":
                    continue
                month = month_of("", c[0])
                if not month or (year, month) not in window:
                    continue
                out.append({"year": year, "month": month, "day": day_of(c[0]), "title": c[1], "platforms": c[2],
                            "type": c[3], "genre": c[4], "developer": c[5], "publisher": c[6]})
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            errors.append(f"wikipedia games {year}: {exc}")
    return out


def verify_tmdb(sids: list[str]) -> int:
    api_key = os.environ.get("TMDB_API_KEY", "").strip()
    if not api_key:
        print("TMDB_API_KEY is not configured")
        return 1
    snapshot = json.loads((CAND / "latest.json").read_text(encoding="utf-8"))
    movies = {movie["sid"]: movie for movie in snapshot["movies"]}
    failed = False
    with TemporaryDirectory() as folder:
        for sid in sids:
            if sid not in movies:
                print(f"Douban sid {sid!r} is missing from candidates/latest.json")
                failed = True
                continue
            try:
                meta = tmdb_candidate_poster(movies[sid], Path(folder) / "poster.jpg", api_key)
            except (ValueError, ImportError, OSError) as exc:
                meta = {"status": "unavailable", "reason": str(exc)}
            print(json.dumps({"sid": sid, "title": movies[sid]["title"], **meta}, ensure_ascii=False))
            failed |= meta["status"] != "ready"
    return int(failed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", help="override the Beijing date (YYYY-MM-DD), for testing")
    parser.add_argument("--skip-candidates", action="store_true", help="only roll the window")
    parser.add_argument("--verify-tmdb", nargs="+", metavar="SID",
                        help="check TMDB for these candidate Douban IDs without updating repository files")
    args = parser.parse_args()
    if args.verify_tmdb:
        return verify_tmdb(args.verify_tmdb)
    today = date.fromisoformat(args.today) if args.today else datetime.now(BJ).date()
    months = window_for(today)
    rolled = []
    for name, key in FILES:
        path = ROOT / name
        data = json.loads(path.read_text(encoding="utf-8"))
        if roll(data, key, months):
            path.write_text(json.dumps(data, ensure_ascii=False, separators=(", ", ": ")), encoding="utf-8")
            rolled.append(name)
    print(json.dumps({"window": months, "rolled": rolled}, ensure_ascii=False))
    if args.skip_candidates:
        return 0
    CAND.mkdir(exist_ok=True)
    for old in (CAND / "posters").glob("*.jpg") if (CAND / "posters").exists() else []:
        old.unlink()
    errors: list[str] = []
    result = {"generated_at": datetime.now(BJ).strftime("%Y-%m-%d %H:%M:%S"),
              "window": [{"year": y, "month": m} for y, m in months],
              "movies": collect_movies(months, errors),
              "music": collect_music(months, errors),
              "games": collect_games(months, errors),
              "errors": errors}
    (CAND / "latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"movies": len(result["movies"]),
                      "music": {k: len(v) for k, v in result["music"].items()},
                      "games": len(result["games"]), "errors": errors}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
