#!/usr/bin/env python3
"""Write a library.json INSIDE each folder that has .pgn or .txt files.

    python build_pgn_library.py -i saved_games

saved_games/cheesecake/library.json holds the cheesecake games,
saved_games/french_defense/library.json holds the French games, etc.
In the app's Library modal, Load JSON takes one or several of them.
Files with several games are split; titles come from the White/Black
headers, else the file name (+ #n). A .txt can hold From Position snippets
([Variant]/[FEN] + moves); .txt chunks with no chess in them (plain notes) are
skipped. Other files (.md, ...) are ignored.
Re-run after adding games; library.json files are overwritten.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def header(pgn, tag):
    m = re.search(r'\[' + tag + r'\s+"([^"]*)"\]', pgn)
    return m.group(1) if m else ""


TAG = re.compile(r'^\s*\[[A-Za-z0-9_]+\s+"')
CHESS = re.compile(r'\[(FEN|Event|Variant)\s+"|(^|\s)\d+\.(\.\.)?\s*(O-O|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8]|0-0)')


def split_games(text):
    """A new game starts at a tag line ([Event], [Variant], [FEN]) that follows movetext,
    so multi-game .pgn files and bare From Position snippets both split correctly."""
    out, cur, has_moves = [], [], False
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        is_tag = bool(TAG.match(line))
        if is_tag and has_moves:
            out.append("\n".join(cur))
            cur, has_moves = [], False
        if not is_tag and line.strip():
            has_moves = True
        cur.append(line)
    out.append("\n".join(cur))
    return [c.strip() for c in out if c.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", default="saved_games")
    args = ap.parse_args()

    root = Path(args.input)
    if not root.is_dir():
        sys.exit(f"not a folder: {root}")

    for d in sorted([root] + [p for p in root.rglob("*") if p.is_dir()]):
        files = sorted([*d.glob("*.pgn"), *d.glob("*.txt")], key=lambda p: p.name.lower())
        if not files:
            continue
        folder = "/".join(d.relative_to(root).parts)
        games = []
        for f in files:
            chunks = split_games(f.read_text(encoding="utf-8", errors="replace"))
            if f.suffix.lower() == ".txt":
                chunks = [c for c in chunks if CHESS.search(c)]
            for n, pgn in enumerate(chunks):
                w, b = header(pgn, "White"), header(pgn, "Black")
                title = f"{w or '?'} vs {b or '?'}" if (w or b) else f.stem + (f" #{n + 1}" if len(chunks) > 1 else "")
                games.append({"title": title, "folder": folder, "file": f.name, "pgn": pgn})
        if not games:
            continue
        out = d / "library.json"
        out.write_text(json.dumps({"version": 1, "games": games}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{out}: {len(games)} games")
        for g in games:
            print(f"    {g['title']}  ({g['file']})")


if __name__ == "__main__":
    main()
