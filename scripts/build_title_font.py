"""Rebuild the bundled serif subset font used by desktop titles.

Needs fontTools with brotli (pip install fonttools brotli) and a Noto Serif SC /
Noto Serif CJK SC Bold source font. Not part of the daily workflow; run it only
when check_data.py warns that the subset lacks characters used in titles.

    python scripts/build_title_font.py --source path/to/NotoSerifCJK-Bold.ttc --font-number 2
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHARS = ROOT / "fonts" / "title-serif-chars.txt"
OUTPUT = ROOT / "fonts" / "title-serif-sc-bold.woff2"
PUNCTUATION = "：；，。、！？（）《》「」『』【】〈〉…—·～"


def wanted_chars() -> str:
    chars: list[str] = []
    for hi in range(0xB0, 0xD8):          # GB2312 level-1 common characters
        for lo in range(0xA1, 0xFF):
            try:
                chars.append(bytes([hi, lo]).decode("gb2312"))
            except UnicodeDecodeError:
                pass
    if CHARS.exists():                     # keep everything already covered
        chars += list(CHARS.read_text(encoding="utf-8").strip())
    for name, key in (("releases.json", "games"), ("movies.json", "movies")):
        data = json.loads((ROOT / name).read_text(encoding="utf-8"))
        for group in data.get("groups", []):
            for item in group.get(key, []):
                chars += [c for c in str(item.get("title", ""))
                          if "　" <= c <= "鿿" or "＀" <= c <= "￯"]
    chars += list(PUNCTUATION)
    return "".join(dict.fromkeys(chars))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="Noto Serif SC Bold font file (.otf/.ttf/.ttc)")
    parser.add_argument("--font-number", default="0", help="index inside a .ttc (Noto Serif CJK: SC is 2)")
    args = parser.parse_args()
    text = wanted_chars()
    CHARS.write_text(text + "\n", encoding="utf-8")
    subprocess.run([sys.executable, "-m", "fontTools.subset", args.source,
                    f"--font-number={args.font_number}", f"--text-file={CHARS}",
                    "--flavor=woff2", f"--output-file={OUTPUT}",
                    "--layout-features=kern,palt,vert", "--no-hinting", "--desubroutinize",
                    "--name-IDs=*"], check=True)
    print(f"{OUTPUT.name}: {len(text)} characters, {OUTPUT.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
