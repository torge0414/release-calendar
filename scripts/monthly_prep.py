"""Monthly preparation: roll the three-month window and collect candidate data.

Runs in GitHub Actions on the 1st of each month (08:00 Beijing), before Claude's
monthly curation task. It only does deterministic work and never chooses titles:

1. Roll releases.json / movies.json / albums.json to the new window
   (previous, current, next month). Groups that leave the window are dropped,
   new months start empty, existing entries are untouched.
2. Collect candidates into candidates/latest.json:
   - movies: Douban "now showing" + "coming soon" (heat: wish / rating counts),
     details for titles inside the window, and posters for titles that pass the
     heat line, saved to candidates/posters/ (Douban blocks hotlinking).
   - music: Apple Music US most-played albums, Metacritic coming-soon list,
     Wikipedia "List of <year> albums", Wikipedia "<year> in South Korean music",
     plus iTunes lookups (genre, track count, artwork, China storefront link).
   - games: Wikipedia "<year> in video games" release tables.
Every source is optional: a failure is recorded in "errors" and the rest go on.
Standard library only, like the other scripts.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "candidates"
BJ = timezone(timedelta(hours=8))
TIMEOUT = 30
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
MOVIE_HEAT = 5000          # HANDOVER §4B：想看或评分人数
DOUBAN_DELAY = 3.5         # 豆瓣对同一 IP 限流，请求之间至少 3 秒
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

def douban(path: str):
    time.sleep(DOUBAN_DELAY)
    return fetch_json("https://m.douban.com/rexxar/api/v2/" + path, {"User-Agent": MOBILE_UA, "Referer": "https://m.douban.com/movie/"})


def collect_movies(months, errors) -> list[dict]:
    items = {}
    for coll in ("movie_showing", "movie_soon"):
        try:
            for x in douban(f"subject_collection/{coll}/items?start=0&count=60").get("subject_collection_items", []):
                r = x.get("rating") or {}
                items[str(x["id"])] = {"sid": str(x["id"]), "title": x.get("title"), "list": coll,
                                       "release_hint": x.get("release_date"), "wish": x.get("wish_count"),
                                       "score": r.get("value"), "votes": r.get("count")}
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
            errors.append(f"douban {coll}: {exc}")
    window = {(y, m) for y, m in months}
    out = []
    for sid, it in items.items():
        try:
            j = douban(f"movie/{sid}?ck=&for_mobile=1")
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            errors.append(f"douban movie {sid}: {exc}")
            if "1309" in str(exc) or "429" in str(exc):
                break
            continue
        pub = ";".join(j.get("pubdate") or [])
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})\(中国大陆\)", pub)
        mainland = date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
        r = j.get("rating") or {}
        it.update({"pubdate": pub, "mainland_date": mainland.isoformat() if mainland else None,
                   "year": j.get("year"), "genres": j.get("genres"), "countries": j.get("countries"),
                   "directors": [d.get("name") for d in j.get("directors") or []],
                   "actors": [a.get("name") for a in (j.get("actors") or [])[:3]],
                   "score": r.get("value"), "votes": r.get("count"), "comments": j.get("comment_count"),
                   "null_rating_reason": j.get("null_rating_reason"), "poster_url": (j.get("pic") or {}).get("large")})
        it["in_window"] = bool(mainland and (mainland.year, mainland.month) in window)
        it["heat_ok"] = max(it.get("wish") or 0, it.get("votes") or 0) >= MOVIE_HEAT
        out.append(it)
    # 过线、在窗口内、仓库里还没有本地海报的，先把海报下好
    (CAND / "posters").mkdir(parents=True, exist_ok=True)
    for it in out:
        if not (it["in_window"] and it["heat_ok"] and it.get("poster_url")):
            continue
        target = CAND / "posters" / f"movie_{it['sid']}.jpg"
        if (ROOT / "img" / target.name).exists():
            it["poster_file"] = f"img/{target.name}"
            continue
        try:
            data = fetch(it["poster_url"], {"Referer": "https://m.douban.com/"}, binary=True)
            if data[:3] != b"\xff\xd8\xff":
                raise ValueError("not a JPEG")
            target.write_bytes(data)
            it["poster_file"] = f"candidates/posters/{target.name}"
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            errors.append(f"douban poster {it['sid']}: {exc}")
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
            for r in wiki_rows(f"List of {year} albums"):
                c = r["cells"]
                if len(c) < 4:
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
                if len(c) < 3 or not month or (year, month) not in window:
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
            if src == "wikipedia" and not it["album_has_article"]:
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
            for r in wiki_rows(f"{year} in video games"):
                c = r["cells"]
                if len(c) < 3:
                    continue
                month = month_of(r["section"], c[0])
                if not month or (year, month) not in window:
                    continue
                out.append({"year": year, "month": month, "section": r["section"], "cells": c})
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            errors.append(f"wikipedia games {year}: {exc}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", help="override the Beijing date (YYYY-MM-DD), for testing")
    parser.add_argument("--skip-candidates", action="store_true", help="only roll the window")
    args = parser.parse_args()
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
