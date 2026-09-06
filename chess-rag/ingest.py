#!/usr/bin/env python3
"""
Phase 1 — Ingest: pull the last 100 Chess.com games into a per-user bucket.

Usage (from chess-rag/):
    python ingest.py <username>
    python ingest.py <username> --max 50

Usage (from inside a bucket folder — incremental refresh, no args needed):
    cd data/<username>
    python ingest.py

The username doubles as the bucket key. Everything lands in data/<username>/:
    raw/chesscom/<game_id>.pgn   one annotated PGN per game
    games.pgn                    merged, de-duplicated store
    state.json                   last_fetched_at for incremental runs
Plus copies of the pipeline scripts (ingest/tree_engine/tree_viz/report),
making the bucket self-contained — cd in and run any script with no args.
The bucket folder can be copied anywhere as-is (e.g. shared with a friend).

On first run:
    Walks Chess.com archives newest → oldest until max_games collected.

On subsequent runs:
    Only fetches games newer than last_fetched_at, merges with existing
    raw PGNs, then re-trims to the most recent max_games total.

Engine annotation (on by default, requires a stockfish binary):
    Each newly fetched PGN is run through Stockfish: played moves get
    ?! / ? / ?? glyphs, refuted moves get the best line as a variation,
    and every move gets a [%eval ±x.xx] comment. tree_viz/report viewers
    render these variations automatically, and report.py's GPT prompt
    includes them. Annotated games carry an [EngineAnalysis] header so
    they are never re-analyzed. Flags: --no-analyze, --depth N,
    --analyze-all (backfill existing PGNs).
"""

import argparse
import io
import json
import os
import re
import shutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests

try:
    import chess
    import chess.engine
    import chess.pgn
    HAVE_CHESS = True
except ImportError:
    HAVE_CHESS = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
RAW_CHESSCOM_DIR = os.path.join(DATA_DIR, "raw", "chesscom")
GAMES_PGN_PATH = os.path.join(DATA_DIR, "games.pgn")
STATE_PATH = os.path.join(DATA_DIR, "state.json")

# Pipeline scripts copied into every bucket so it runs standalone.
SCRIPTS_TO_COPY = ["ingest.py", "tree_engine.py", "tree_viz.py", "report.py"]

# Engine annotation thresholds (centipawns lost, from the mover's perspective)
BLUNDER_CP = 200      # ??
MISTAKE_CP = 100      # ?
INACCURACY_CP = 50    # ?!
PV_LENGTH = 5         # moves of best line embedded as a variation

NAG_GLYPHS = {1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!"}


def use_bucket(bucket_dir: str) -> None:
    """Point all storage paths at the bucket folder (called from main before any I/O)."""
    global DATA_DIR, RAW_CHESSCOM_DIR, GAMES_PGN_PATH, STATE_PATH
    DATA_DIR = bucket_dir
    RAW_CHESSCOM_DIR = os.path.join(DATA_DIR, "raw", "chesscom")
    GAMES_PGN_PATH = os.path.join(DATA_DIR, "games.pgn")
    STATE_PATH = os.path.join(DATA_DIR, "state.json")


def copy_scripts(bucket_dir: str) -> None:
    """Copy the pipeline scripts into the bucket (keeps bucket copies in sync)."""
    for name in SCRIPTS_TO_COPY:
        src = os.path.join(HERE, name)
        dst = os.path.join(bucket_dir, name)
        if not os.path.exists(src):
            continue
        if os.path.abspath(src) == os.path.abspath(dst):
            continue  # already running inside the bucket
        shutil.copy2(src, dst)

HEADERS = {
    "User-Agent": "chess-rag-ingest/1.0 (personal use)",
    "Accept": "application/json",
}
ARCHIVE_DELAY = 0.5  # seconds between archive requests, as per spec


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# PGN helpers
# ---------------------------------------------------------------------------

def extract_header(pgn: str, key: str) -> str | None:
    m = re.search(rf'\[{re.escape(key)}\s+"([^"]*)"\]', pgn)
    return m.group(1) if m else None


def extract_game_url(pgn: str) -> str | None:
    return extract_header(pgn, "Link") or extract_header(pgn, "Site")


def extract_game_id_from_url(url: str) -> str | None:
    m = re.search(r"/game/(?:live|daily)/(\d+)", url)
    return m.group(1) if m else None


def inject_headers(pgn: str, extra: dict) -> str:
    """Insert extra [Key "Value"] lines after the last existing PGN header."""
    lines = pgn.split("\n")
    last_header_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("["):
            last_header_idx = i
    new_headers = [f'[{k} "{v}"]' for k, v in extra.items()]
    lines = lines[: last_header_idx + 1] + new_headers + lines[last_header_idx + 1 :]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Chess.com fetcher
# ---------------------------------------------------------------------------

def fetch_chesscom_games(
    username: str,
    max_games: int = 100,
    since_timestamp: int | None = None,
    months: int | None = None,
) -> list[dict]:
    """
    Fetch raw game dicts from Chess.com (newest first).

    Stops when max_games is reached, a game older than since_timestamp is seen,
    or (if months is set) after walking that many monthly archives.
    Adds ARCHIVE_DELAY between each monthly archive request.
    """
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    resp = requests.get(archives_url, headers=HEADERS, timeout=15)
    if resp.status_code == 404:
        raise SystemExit(f"User '{username}' not found on Chess.com.")
    resp.raise_for_status()
    archive_urls: list[str] = resp.json().get("archives", [])

    if not archive_urls:
        return []

    # --months: only look at the N most recent monthly archives
    if months is not None:
        archive_urls = archive_urls[-months:]
        print(f"  Limiting to last {months} month(s): {archive_urls[0].split('/')[-2]}/{archive_urls[0].split('/')[-1]} → {archive_urls[-1].split('/')[-2]}/{archive_urls[-1].split('/')[-1]}")

    collected: list[dict] = []

    for archive_url in reversed(archive_urls):  # newest month first
        if len(collected) >= max_games:
            break

        time.sleep(ARCHIVE_DELAY)

        try:
            r = requests.get(archive_url, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  [warn] Skipping {archive_url}: {e}")
            continue

        month_games: list[dict] = r.json().get("games", [])

        for game in reversed(month_games):  # newest first within month
            end_time: int = game.get("end_time", 0)
            if since_timestamp is not None and end_time <= since_timestamp:
                # Hit games we already have — stop walking entirely
                return collected
            collected.append(game)
            if len(collected) >= max_games:
                break

    return collected


# ---------------------------------------------------------------------------
# Lichess fetcher (stub — disabled pending lichess-org/api#667)
# ---------------------------------------------------------------------------

def fetch_lichess_games(
    username: str,
    max_games: int = 100,
    since_timestamp: int | None = None,
) -> list[dict]:
    """
    Stub for Lichess ingestion.

    Will be implemented once lichess-org/api#667 is resolved.
    The API endpoint is: GET https://lichess.org/api/games/user/{username}
    with params: max, pgnInJson=true, opening=true, sort=dateDesc
    """
    raise NotImplementedError(
        "Lichess fetcher is not yet enabled (see lichess-org/api#667). "
        "Use Chess.com for now."
    )


# ---------------------------------------------------------------------------
# Game dict → annotated PGN
# ---------------------------------------------------------------------------

def build_annotated_pgn(game: dict, my_username: str) -> str | None:
    """
    Turn a raw Chess.com game dict into a PGN with extra metadata tags.

    Added headers:
        Source, MyColor, MyResult, OpponentUsername, OpponentRating
    Returns None if the game has no PGN field.
    """
    pgn = game.get("pgn")
    if not pgn:
        return None

    white = game.get("white", {})
    black = game.get("black", {})

    if my_username.lower() == white.get("username", "").lower():
        my_color = "white"
        my_result_raw = white.get("result", "")
        opp = black
    else:
        my_color = "black"
        my_result_raw = black.get("result", "")
        opp = white

    if my_result_raw == "win":
        my_result = "win"
    elif opp.get("result", "") == "win":
        my_result = "loss"
    else:
        my_result = "draw"

    extra = {
        "Source": "chess.com",
        "MyColor": my_color,
        "MyResult": my_result,
        "OpponentUsername": opp.get("username", "?"),
        "OpponentRating": str(opp.get("rating", "?")),
    }
    return inject_headers(pgn, extra)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def save_raw_pgn(game_id: str, pgn: str) -> None:
    os.makedirs(RAW_CHESSCOM_DIR, exist_ok=True)
    with open(os.path.join(RAW_CHESSCOM_DIR, f"{game_id}.pgn"), "w") as f:
        f.write(pgn)


def load_existing_game_ids() -> set[str]:
    if not os.path.exists(RAW_CHESSCOM_DIR):
        return set()
    return {f[:-4] for f in os.listdir(RAW_CHESSCOM_DIR) if f.endswith(".pgn")}


def _sort_key(fname: str) -> int:
    """Numeric sort key for a game ID filename; Chess.com IDs are monotonically increasing."""
    stem = fname[:-4]  # strip .pgn
    return int(stem) if stem.isdigit() else 0


def rebuild_games_pgn() -> None:
    """Rebuild data/games.pgn from all raw/chesscom PGNs, newest → oldest."""
    fnames = sorted(
        [f for f in os.listdir(RAW_CHESSCOM_DIR) if f.endswith(".pgn")],
        key=_sort_key,
        reverse=True,  # newest first
    )

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(GAMES_PGN_PATH, "w") as out:
        for fname in fnames:
            with open(os.path.join(RAW_CHESSCOM_DIR, fname)) as f:
                out.write(f.read().strip() + "\n\n")

    print(f"  Wrote {len(fnames)} games → {GAMES_PGN_PATH}")


# ---------------------------------------------------------------------------
# Engine annotation (Stockfish)
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


def annotate_pgn(engine, pgn_text: str, depth: int) -> str | None:
    """
    Return pgn_text with engine analysis embedded along the mainline:
      - ?! / ? / ?? glyphs on played moves (by centipawn loss)
      - the best line as a ( … ) variation when a move lost >= MISTAKE_CP
      - a [%eval ±x.xx] comment on every move
    Scores are normalized to White's perspective; losses are measured from
    the mover's perspective (single pass, eval carried forward).
    Returns None if the game can't be parsed.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None or not list(game.mainline_moves()):
        return None

    def evaluate(board) -> tuple[int, list]:
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

        # Refuted? Embed the best line as a variation from the same position.
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
    # python-chess writes NAGs as $n codes; convert to glyphs for viewer display
    out = re.sub(r"\$(\d+)", lambda m: NAG_GLYPHS.get(int(m.group(1)), ""), out)
    return out


def _annotate_worker(
    paths: list[tuple[str, str]],
    depth: int,
    sf_path: str,
    sf_threads: int,
    counter: list,
    counter_lock: threading.Lock,
) -> None:
    """Worker: opens its own Stockfish instance and annotates a slice of games."""
    engine = chess.engine.SimpleEngine.popen_uci(sf_path)
    if sf_threads > 1:
        engine.configure({"Threads": sf_threads})
    try:
        for gid, path in paths:
            with open(path) as f:
                text = f.read()
            if extract_header(text, "EngineAnalysis"):
                continue
            try:
                annotated = annotate_pgn(engine, text, depth)
            except Exception as e:
                print(f"    [warn] annotation failed for {gid}: {e}")
                continue
            if annotated:
                with open(path, "w") as f:
                    f.write(annotated.rstrip() + "\n")
            with counter_lock:
                counter[0] += 1
                print(f"  Annotated {counter[0]}: {gid} (depth {depth})")
    finally:
        engine.quit()


def annotate_games(
    paths: list[tuple[str, str]],
    depth: int,
    parallel: int = 1,
    sf_threads: int = 1,
) -> None:
    """
    Annotate each (game_id, path) in place; skips files already annotated.

    parallel:   number of simultaneous Stockfish processes (default 1)
    sf_threads: CPU threads per Stockfish instance (default 1)

    Total CPU cores used ≈ parallel × sf_threads.
    Example: --parallel 4 --sf-threads 4 uses ~16 cores.
    """
    if not paths:
        return
    if not HAVE_CHESS:
        print("  [warn] python-chess not installed — skipping engine annotation")
        return
    sf_path = find_stockfish()
    if not sf_path:
        print("  [warn] stockfish binary not found — skipping engine annotation")
        return

    # Filter already-annotated files up front
    todo = [(gid, p) for gid, p in paths
            if not extract_header(open(p).read(), "EngineAnalysis")]
    if not todo:
        print("  All games already annotated.")
        return

    print(f"  Annotating {len(todo)} game(s) — parallel={parallel} sf_threads={sf_threads} depth={depth}")

    counter: list[int] = [0]
    counter_lock = threading.Lock()

    if parallel == 1:
        _annotate_worker(todo, depth, sf_path, sf_threads, counter, counter_lock)
        return

    # Split work evenly across workers
    chunk = max(1, len(todo) // parallel)
    slices = [todo[i:i + chunk] for i in range(0, len(todo), chunk)]

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = [
            pool.submit(_annotate_worker, s, depth, sf_path, sf_threads, counter, counter_lock)
            for s in slices
        ]
        for f in as_completed(futures):
            f.result()  # re-raise any worker exception


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest recent Chess.com games into a per-user bucket"
    )
    parser.add_argument(
        "username", nargs="?", help="Chess.com username "
        "(optional when running inside an existing bucket folder)",
    )
    parser.add_argument(
        "--max", type=int, default=None, metavar="N",
        help="Max games to keep (default: 100, or unlimited when --months is set)",
    )
    parser.add_argument(
        "--months", type=int, default=None, metavar="M",
        help="Fetch only the last M months of archives (e.g. --months 6)",
    )
    parser.add_argument(
        "--depth", type=int, default=15, metavar="D",
        help="Stockfish analysis depth (default: 15)",
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Ignore last_fetched_at and re-fetch from scratch (use with --months)",
    )
    parser.add_argument(
        "--no-analyze", action="store_true",
        help="Skip Stockfish annotation of fetched games",
    )
    parser.add_argument(
        "--analyze-all", action="store_true",
        help="Also annotate existing raw PGNs that lack analysis",
    )
    parser.add_argument(
        "--parallel", type=int, default=1, metavar="N",
        help="Number of simultaneous Stockfish processes (default: 1)",
    )
    parser.add_argument(
        "--sf-threads", type=int, default=1, metavar="N",
        help="CPU threads per Stockfish instance (default: 1)",
    )
    args = parser.parse_args()

    # A copied script inside data/<key>/ treats its own folder as the bucket.
    in_bucket = os.path.basename(os.path.dirname(HERE)) == "data"
    if in_bucket:
        use_bucket(HERE)
    else:
        if not args.username:
            parser.error("username required (e.g. python ingest.py TTTstanley)")
        use_bucket(os.path.join(HERE, "data", args.username.strip().lower()))

    username = (args.username or "").strip().lower()
    # No cap by default; --max adds an explicit ceiling if needed
    max_games = args.max if args.max is not None else 10_000

    state = load_state()
    if not username:
        username = state.get("chesscom", {}).get("username", "")
    if not username:
        parser.error("no username given and none recorded in state.json yet")

    print(f"Bucket: {DATA_DIR}")

    since_ts: int | None = None if args.full else state.get("chesscom", {}).get("last_fetched_at")
    existing_ids = load_existing_game_ids()

    if since_ts:
        when = datetime.fromtimestamp(since_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        print(f"Incremental run — fetching games newer than {when} for {username}")
    else:
        print(f"{'Full' if args.full else 'First'} run — fetching all games for {username}")

    raw_games = fetch_chesscom_games(username, max_games=max_games, since_timestamp=since_ts, months=args.months)
    print(f"  Retrieved {len(raw_games)} game(s) from Chess.com API")

    new_count = 0
    new_ids: list[str] = []
    latest_end_time: int = since_ts or 0

    for game in raw_games:
        pgn = build_annotated_pgn(game, username)
        if not pgn:
            continue

        url = extract_game_url(pgn)
        game_id = (extract_game_id_from_url(url) if url else None) or str(
            game.get("end_time", "unknown")
        )

        if game_id in existing_ids:
            continue

        save_raw_pgn(game_id, pgn)
        existing_ids.add(game_id)
        new_count += 1
        new_ids.append(game_id)

        end_time = game.get("end_time", 0)
        if end_time > latest_end_time:
            latest_end_time = end_time

    print(f"  Saved {new_count} new PGN file(s) to {RAW_CHESSCOM_DIR}")

    if not args.no_analyze:
        targets = [(gid, os.path.join(RAW_CHESSCOM_DIR, f"{gid}.pgn")) for gid in new_ids]
        if args.analyze_all:
            seen = set(new_ids)
            targets += [
                (gid, os.path.join(RAW_CHESSCOM_DIR, f"{gid}.pgn"))
                for gid in sorted(load_existing_game_ids())
                if gid not in seen
            ]
        annotate_games(targets, args.depth, parallel=args.parallel, sf_threads=args.sf_threads)

    rebuild_games_pgn()

    state.setdefault("chesscom", {}).update(
        {"last_fetched_at": latest_end_time, "username": username}
    )
    save_state(state)
    print(f"  State saved → {STATE_PATH}")

    copy_scripts(DATA_DIR)
    print(f"  Pipeline scripts synced → {DATA_DIR}")
    print("Done.")


if __name__ == "__main__":
    main()
