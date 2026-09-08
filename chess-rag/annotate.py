#!/usr/bin/env python3
"""
Standalone Stockfish annotator for arbitrary PGN files.
Optionally runs the full tree pipeline (merge → tree_engine → tree_viz) afterwards.

Adds ?! / ? / ?? glyphs, best-line variations, and [%eval] comments to each
game's mainline.  Already-annotated files (containing [EngineAnalysis] header)
are skipped so the script is safe to re-run.

Usage:
    # Annotate + build tree viewer in one shot (target must be a directory)
    python annotate.py against_computer/pgns/ --build

    # Annotate only
    python annotate.py against_computer/pgns/

    # Single file (no --build)
    python annotate.py against_computer/pgns/JDekiJ7J.pgn

    # Custom depth / parallelism
    python annotate.py against_computer/pgns/ --depth 15 --parallel 2 --sf-threads 4 --build

--build writes games.pgn, tree.sqlite, and tree_viewer.html into the parent of
the pgns/ directory (e.g. against_computer/) and opens the viewer automatically.
"""

import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import chess
    import chess.engine
    import chess.pgn
    HAVE_CHESS = True
except ImportError:
    HAVE_CHESS = False

# ---------------------------------------------------------------------------
# Constants (kept in sync with ingest.py)
# ---------------------------------------------------------------------------

BLUNDER_CP = 200
MISTAKE_CP = 100
INACCURACY_CP = 50
PV_LENGTH = 5

NAG_GLYPHS = {1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_stockfish() -> str | None:
    """Locate a stockfish binary."""
    for cand in [shutil.which("stockfish"),
                 "/opt/homebrew/bin/stockfish",
                 "/usr/local/bin/stockfish"]:
        if cand and os.path.exists(cand):
            return cand
    return None


def _fmt_eval(cp_white: int) -> str:
    """Format a White-POV centipawn score as PGN [%eval] value."""
    if abs(cp_white) >= 9900:
        n = 10000 - abs(cp_white)
        return f"#{'' if cp_white > 0 else '-'}{n}"
    return f"{cp_white / 100:.2f}"


def _has_engine_analysis(pgn_text: str) -> bool:
    return bool(re.search(r'\[EngineAnalysis\s+"[^"]*"\]', pgn_text))


# ---------------------------------------------------------------------------
# Core annotation (same logic as ingest.py annotate_pgn)
# ---------------------------------------------------------------------------

def annotate_pgn(engine, pgn_text: str, depth: int) -> str | None:
    """
    Return pgn_text with engine analysis embedded along the mainline.
    Returns None if the game can't be parsed.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None or not list(game.mainline_moves()):
        return None

    def evaluate(board):
        info = engine.analyse(board, chess.engine.Limit(depth=depth))
        return info["score"].white().score(mate_score=10000), info.get("pv", [])

    board = game.board()
    prev_white, prev_pv = evaluate(board)

    node = game
    while node.variations:
        next_node = node.variations[0]
        move = next_node.move
        mover_white = board.turn == chess.WHITE
        pre_board = board.copy()
        board.push(move)

        cur_white, cur_pv = evaluate(board)
        loss = (prev_white - cur_white) if mover_white else (cur_white - prev_white)

        if loss >= BLUNDER_CP:
            next_node.nags.add(chess.pgn.NAG_BLUNDER)
        elif loss >= MISTAKE_CP:
            next_node.nags.add(chess.pgn.NAG_MISTAKE)
        elif loss >= INACCURACY_CP:
            next_node.nags.add(chess.pgn.NAG_DUBIOUS_MOVE)

        eval_tag = f"[%eval {_fmt_eval(cur_white)}]"
        next_node.comment = (
            f"{next_node.comment} {eval_tag}" if next_node.comment else eval_tag
        )

        if loss >= MISTAKE_CP and prev_pv and prev_pv[0] != move:
            var = node.add_variation(prev_pv[0])
            var.comment = f"best {_fmt_eval(prev_white)}"
            pre_board.push(prev_pv[0])
            cur_var = var
            for m in prev_pv[1:PV_LENGTH]:
                if m in pre_board.legal_moves:
                    cur_var = cur_var.add_variation(m)
                    pre_board.push(m)

        prev_white, prev_pv = cur_white, cur_pv
        node = next_node

    game.headers["EngineAnalysis"] = f"stockfish depth {depth}"
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    out = game.accept(exporter)
    out = re.sub(r"\$(\d+)", lambda m: NAG_GLYPHS.get(int(m.group(1)), ""), out)
    return out


# ---------------------------------------------------------------------------
# Worker / orchestrator (same pattern as ingest.py)
# ---------------------------------------------------------------------------

def _annotate_worker(
    paths: list[str],
    depth: int,
    sf_path: str,
    sf_threads: int,
    counter: list,
    counter_lock: threading.Lock,
) -> None:
    engine = chess.engine.SimpleEngine.popen_uci(sf_path)
    if sf_threads > 1:
        engine.configure({"Threads": sf_threads})
    try:
        for path in paths:
            with open(path) as f:
                text = f.read()
            if _has_engine_analysis(text):
                print(f"  Already annotated, skipping: {os.path.basename(path)}")
                continue
            try:
                annotated = annotate_pgn(engine, text, depth)
            except Exception as e:
                print(f"  [warn] annotation failed for {os.path.basename(path)}: {e}")
                continue
            if annotated:
                with open(path, "w") as f:
                    f.write(annotated.rstrip() + "\n")
            with counter_lock:
                counter[0] += 1
                print(f"  Annotated {counter[0]}: {os.path.basename(path)} (depth {depth})")
    finally:
        engine.quit()


def annotate_files(paths: list[str], depth: int, parallel: int = 1, sf_threads: int = 1) -> None:
    if not paths:
        print("No PGN files found.")
        return
    if not HAVE_CHESS:
        print("[error] python-chess not installed — pip install chess")
        return
    sf_path = find_stockfish()
    if not sf_path:
        print("[error] stockfish binary not found — install via brew install stockfish or similar")
        return

    todo = [p for p in paths if not _has_engine_analysis(open(p).read())]
    skipped = len(paths) - len(todo)
    if skipped:
        print(f"  {skipped} file(s) already annotated, skipping.")
    if not todo:
        print("  Nothing to annotate.")
        return

    print(f"  Annotating {len(todo)} file(s) — parallel={parallel} sf_threads={sf_threads} depth={depth}")

    counter: list[int] = [0]
    counter_lock = threading.Lock()

    if parallel == 1:
        _annotate_worker(todo, depth, sf_path, sf_threads, counter, counter_lock)
        return

    chunk = max(1, len(todo) // parallel)
    slices = [todo[i:i + chunk] for i in range(0, len(todo), chunk)]

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = [
            pool.submit(_annotate_worker, s, depth, sf_path, sf_threads, counter, counter_lock)
            for s in slices
        ]
        for f in as_completed(futures):
            f.result()


# ---------------------------------------------------------------------------
# Tree pipeline
# ---------------------------------------------------------------------------

def build_tree(pgn_dir: Path) -> None:
    """Merge PGNs → games.pgn, run tree_engine, run tree_viz."""
    here = Path(__file__).parent
    out_dir = pgn_dir.parent  # e.g. against_computer/

    # 1. Merge individual PGNs into games.pgn
    games_pgn = out_dir / "games.pgn"
    pgn_files = sorted(pgn_dir.glob("*.pgn"))
    print(f"\nMerging {len(pgn_files)} PGN(s) → {games_pgn}")
    with open(games_pgn, "w") as out:
        for p in pgn_files:
            out.write(p.read_text(encoding="utf-8").strip() + "\n\n")

    # 2. tree_engine
    db_path = out_dir / "tree.sqlite"
    print(f"Building tree → {db_path}")
    subprocess.run(
        [sys.executable, str(here / "tree_engine.py"),
         "--pgn", str(games_pgn), "--db", str(db_path)],
        check=True,
    )

    # 3. tree_viz
    viewer_path = out_dir / "tree_viewer.html"
    print(f"Generating viewer → {viewer_path}")
    subprocess.run(
        [sys.executable, str(here / "tree_viz.py"),
         "--db", str(db_path),
         "--pgn-dir", str(pgn_dir),
         "--out", str(viewer_path)],
        check=True,
    )

    print(f"\nDone. Open: {viewer_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Annotate PGN files with Stockfish, then optionally build the tree viewer"
    )
    parser.add_argument(
        "target",
        help="A .pgn file or a directory containing .pgn files",
    )
    parser.add_argument(
        "--depth", type=int, default=15,
        help="Stockfish analysis depth per move (default: 15)",
    )
    parser.add_argument(
        "--parallel", type=int, default=1,
        help="Number of simultaneous Stockfish processes (default: 1)",
    )
    parser.add_argument(
        "--sf-threads", type=int, default=1, dest="sf_threads",
        help="CPU threads per Stockfish instance (default: 1)",
    )
    parser.add_argument(
        "--build", action="store_true",
        help="After annotation, merge PGNs and run tree_engine + tree_viz (directory target only)",
    )
    args = parser.parse_args()

    target = Path(args.target)
    if target.is_file():
        pgn_paths = [str(target)]
        pgn_dir = None
    elif target.is_dir():
        pgn_paths = sorted(str(p) for p in target.glob("*.pgn"))
        pgn_dir = target
    else:
        parser.error(f"Not a file or directory: {target}")

    annotate_files(pgn_paths, args.depth, parallel=args.parallel, sf_threads=args.sf_threads)

    if args.build:
        if pgn_dir is None:
            parser.error("--build requires a directory target, not a single file")
        build_tree(pgn_dir)


if __name__ == "__main__":
    main()
