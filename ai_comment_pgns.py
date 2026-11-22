#!/usr/bin/env python3
"""AI comments for a folder of PGNs, using the local Ollama model.

Goes through every .pgn under FOLDER (subfolders too), finds the games that
have no comments yet, asks the model for one-line coaching comments and
writes the commented games out. Same idea as the "AI comments on variation
moves" button in index.html:

  - game has variations -> comment the main-line moves that have a variation
    (played move vs the alternative), 8 per request, biggest eval drop first,
    looping until all of them are done
  - no variations       -> comment the 6-12 most instructive moves

The model only returns text. Comments are attached here by move number + SAN,
so moves, variations and [%eval] tags are never changed. Moves that already
have a comment are left alone.

Model routing is the same as lf / server.js: the Mac Studio first
(http://Stanleys-Mac-Studio.local:11434, inkling-2-mini, ~3 s connect
timeout), then this laptop's Ollama (largest qwen model).

Usage:
  python ai_comment_pgns.py saved_games                # -> saved_games/_ai_commented/...
  python ai_comment_pgns.py saved_games --in-place     # overwrite the originals
  python ai_comment_pgns.py saved_games --dry-run      # list what it would ask for
  python ai_comment_pgns.py saved_games --force        # also games that have comments
                                                       # (only their bare moves get filled)
  python ai_comment_pgns.py saved_games --mode key     # key moves even if there are variations
  python ai_comment_pgns.py saved_games --host http://localhost:11434 --model qwen3.5:9b
"""
import argparse
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import chess
import chess.pgn

STUDIO_URL = "http://Stanleys-Mac-Studio.local:11434"
STUDIO_MODEL = "inkling-2-mini"
LAPTOP_URL = "http://localhost:11434"
OUT_DIRNAME = "_ai_commented"
CAP = 8            # moves per request in variation mode (reply length = wait time)
CTX = 32768


# ---------------------------------------------------------------- Ollama
def _get(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def pick_backend(host=None, model=None):
    def choose(url, timeout, preferred=None):
        models = _get(url + "/api/tags", timeout).get("models", [])
        names = [m["name"] for m in models]
        sizes = {m["name"]: m.get("size", 0) for m in models}
        if model:
            return model
        if preferred and (preferred in names or preferred + ":latest" in names):
            return preferred
        qwen = sorted((n for n in names if "qwen" in n.lower()), key=lambda n: -sizes[n])
        if qwen:
            return qwen[0]
        raise RuntimeError(f"No usable model at {url} — pass --model")

    if host:
        host = host.rstrip("/")
        return host, choose(host, 10)
    try:
        return STUDIO_URL, choose(STUDIO_URL, 3, STUDIO_MODEL)
    except Exception as e:
        print(f"Mac Studio not reachable ({e}), using this laptop", file=sys.stderr)
        return LAPTOP_URL, choose(LAPTOP_URL, 5)


def ask(backend, prompt):
    url, model = backend
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {"num_ctx": CTX},
    }).encode()
    req = urllib.request.Request(url + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        content = json.load(r).get("message", {}).get("content", "")
    return re.sub(r"<think>[\s\S]*?</think>", "", content).strip()


# ---------------------------------------------------------------- PGN helpers
def clean(comment):
    """A comment minus [%eval]/[%clk] tags — what counts as a real comment."""
    return re.sub(r"\s+", " ", re.sub(r"\[%(?:eval|clk)[^\]]*\]", "", comment or "")).strip()


def is_opening_note(node):
    """'D00 Queens Pawn Opening' on move 1 is an opening label, not a comment."""
    return node.ply() == 1 and re.match(r"^[A-E]\d\d\b", clean(node.comment))


def main_line(game):
    out, node = [], game
    while node.variations:
        node = node.variations[0]
        out.append(node)
    return out


GLYPH = {1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!"}


def label(node):
    board = node.parent.board()
    num = board.fullmove_number
    marks = "".join(GLYPH.get(n, "") for n in sorted(node.nags))
    return f"{num}{'.' if board.turn == chess.WHITE else '...'} {node.san()}{marks}"


def key_of(node):
    board = node.parent.board()
    return f"{board.fullmove_number}{'.' if board.turn == chess.WHITE else '...'}"


def has_comments(game):
    return any(clean(n.comment) and not is_opening_note(n) for n in main_line(game))


def eval_drop(node):
    """Centipawns the mover gave away, from [%eval] tags; None without them."""
    a, b = node.parent.eval(), node.eval()
    if a is None or b is None:
        return None
    a, b = a.white().score(mate_score=10000), b.white().score(mate_score=10000)
    mover_white = node.parent.board().turn == chess.WHITE
    return (a - b) if mover_white else (b - a)


def movetext(game):
    exporter = chess.pgn.StringExporter(headers=False, variations=True, comments=True)
    return game.accept(exporter)


def bare(node):
    return not clean(node.comment) or is_opening_note(node)


def graft(game, reply, only=None):
    """Attach '12... c6 { ... }' lines to matching main-line moves. Returns count."""
    wanted = {}
    for line in reply.splitlines():
        m = re.match(r"^\s*(?:[-•*]\s*)?(\d+)(\.\.\.|\.)\s*(\S+)?\s*\{([^{}]*)\}", line.replace("**", ""))
        if m and m.group(4).strip():
            wanted.setdefault(m.group(1) + m.group(2), []).append((m.group(3), m.group(4).strip()))
    applied = 0
    strip = lambda s: re.sub(r"[!?+#]+$", "", s or "")
    for node in main_line(game):
        if only is not None and node not in only:
            continue
        entries = wanted.get(key_of(node))
        if not entries or not bare(node):
            continue
        san = node.san()
        hit = next((c for s, c in entries if s and strip(s) == strip(san)), None) or \
              next((c for s, c in entries if not s), None)
        if hit:
            node.comment = (node.comment + " " + hit).strip() if node.comment else hit
            applied += 1
    return applied


HEAD = ("Annotate this chess game with short coaching comments. Output ONLY lines in this exact format, nothing else:\n"
        "8. c4 { Classical cheesecake style. }\n"
        "10... Ne4 { Reasonable idea but easily rebuffed. }\n"
        "Rules:\n")
TAIL = ("- ONE short sentence per comment, about 15 words max, evocative and thematic.\n"
        "- If there are [%eval] tags, use them to find the real turning points.\n"
        "- No markdown, no fences, no extra text — just the lines.\n\n")


def prompt_for(game, batch):
    if batch is None:
        rule = ("- Comment only the 6-12 most instructive moves (turning points, strategic ideas, "
                "critical mistakes). Skip routine moves.\n")
    else:
        rule = ("- Comment EXACTLY these main-line moves, one line each, no others: "
                + ", ".join(label(n) for n in batch) + ".\n"
                "- Each has an alternative line in ( ) right after it in the PGN. "
                "Say why the played move is worse or better than that alternative. "
                "A move marked ? or ?? (or $2 / $4 in the PGN) was a mistake: the alternative was better.\n")
    return HEAD + rule + TAIL + movetext(game)


# ---------------------------------------------------------------- per game
def comment_game(game, backend, mode, dry_run, name):
    line = main_line(game)
    var_moves = [n for n in line if len(n.parent.variations) > 1]
    use_vars = mode == "variations" or (mode == "auto" and var_moves)

    if not use_vars:
        if dry_run:
            print(f"  {name}: would ask for 6-12 key moves ({len(line)} moves, no variations)")
            return 0
        t0 = time.time()
        n = graft(game, ask(backend, prompt_for(game, None)))
        print(f"  {name}: {n} key-move comments ({time.time() - t0:.0f}s)")
        return n

    todo = [n for n in var_moves if bare(n)]
    if not todo:
        print(f"  {name}: every variation move already has a comment")
        return 0
    order = sorted(todo, key=lambda n: -(eval_drop(n) if eval_drop(n) is not None else -10**9))
    if dry_run:
        print(f"  {name}: would ask for {len(todo)} variation moves in batches of {CAP}: "
              + ", ".join(label(n) for n in sorted(todo, key=line.index)))
        return 0

    total = 0
    while order:
        batch = sorted(order[:CAP], key=line.index)
        t0 = time.time()
        reply = ask(backend, prompt_for(game, batch))
        got = graft(game, reply, only=set(batch))
        if not got:
            print("    reply had no usable lines; it started: " + repr(reply[:300]))
        total += got
        print(f"  {name}: {got}/{len(batch)} commented ({time.time() - t0:.0f}s)")
        missed = [n for n in batch if bare(n)]
        order = order[CAP:]
        if missed and got:                 # retry the ones it skipped once, at the end
            order += [n for n in missed if n not in order]
        elif missed:
            print(f"    gave up on: {', '.join(label(n) for n in missed)}")
    return total


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--in-place", action="store_true", help="overwrite the original files")
    ap.add_argument("--out", type=Path, help=f"output folder (default FOLDER/{OUT_DIRNAME})")
    ap.add_argument("--force", action="store_true", help="also games that already have comments")
    ap.add_argument("--mode", choices=["auto", "variations", "key"], default="auto")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--host", help="Ollama URL (skips the Studio/laptop choice)")
    ap.add_argument("--model")
    args = ap.parse_args()

    folder = args.folder.resolve()
    out_root = (args.out or folder / OUT_DIRNAME).resolve()
    files = sorted(p for p in folder.rglob("*.pgn") if out_root not in p.resolve().parents)
    if not files:
        sys.exit(f"No .pgn files under {folder}")

    backend = None
    if not args.dry_run:
        backend = pick_backend(args.host, args.model)
        print(f"Model: {backend[1]} at {backend[0]}")

    done = skipped = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        stream = io.StringIO(text)
        games = []
        while True:
            g = chess.pgn.read_game(stream)
            if g is None:
                break
            games.append(g)
        if not games:
            continue
        rel = path.relative_to(folder)
        print(rel)
        changed = 0
        for i, g in enumerate(games, 1):
            name = f"game {i}" if len(games) > 1 else "game"
            if g.errors:
                print(f"  {name}: parse problems ({g.errors[0]}), skipped")
                skipped += 1
                continue
            if has_comments(g) and not args.force:
                print(f"  {name}: already has comments, skipped (--force to fill bare moves)")
                skipped += 1
                continue
            try:
                changed += comment_game(g, backend, "key" if args.mode == "key" else args.mode,
                                        args.dry_run, name)
            except Exception as e:
                print(f"  {name}: failed — {e}")
        if changed and not args.dry_run:
            dest = path if args.in_place else out_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("\n\n".join(str(g) for g in games) + "\n", encoding="utf-8")
            print(f"  -> {dest}")
            done += 1
    print(f"\n{done} file(s) written, {skipped} game(s) skipped")


if __name__ == "__main__":
    main()
