#!/usr/bin/env python3
"""
Phase 1 — Ingest: pull recent Lichess games into a per-user bucket.

Usage (from chess-rag/):
    python lichess_ingest.py <username>
    python lichess_ingest.py <username> --max 50

Usage (from inside a bucket folder — incremental refresh, no args needed):
    cd data/<username>
    python lichess_ingest.py

Sibling to ingest.py's Chess.com pipeline — shares the same bucket
(data/<username>/), the same state.json, and the same merged games.pgn.
Run both scripts against one username to build a combined bucket:
    raw/lichess/<game_id>.pgn    one annotated PGN per game (GameId header)
    games.pgn                    rebuilt from raw/chesscom + raw/lichess,
                                  merged and sorted newest-first by UTCDate/UTCTime
    state.json                   lichess.last_fetched_at for incremental runs

On first run: fetches up to max_games (default 100), newest first.
On subsequent runs: only fetches games newer than last_fetched_at.

Note on the API: GET https://lichess.org/api/games/user/{username} 404s
with a generic "Page not found" page unless the request carries an
identifying User-Agent (lichess-org/api#667) — handled by HEADERS below.
Optionally set LICHESS_API_TOKEN in the environment for higher rate limits.

Engine annotation (on by default, requires a stockfish binary): same as
ingest.py — reuses its annotate_games() (source-agnostic, works on any
raw/*/*.pgn path). Flags: --no-analyze, --depth N, --analyze-all.
"""

import argparse
import io
import json
import os
import re
from datetime import datetime, timezone

import requests

import ingest  # reuse bucket/state/PGN helpers so both sources share one bucket

HEADERS_BASE = {
    "Accept": "application/x-chess-pgn",
}
LICHESS_TOKEN = os.environ.get("LICHESS_API_TOKEN")

GAME_START_RE = re.compile(r"(?=^\[Event )", re.MULTILINE)


def _repo_root() -> str:
    """chess-rag/ root, whether running the root copy of this script or the
    one synced into data/<username>/ (eco_openings.json lives only at root)."""
    d = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(os.path.dirname(d)) == "data":
        return os.path.dirname(os.path.dirname(d))
    return d


ECO_CACHE_PATH = os.path.join(_repo_root(), "eco_openings.json")


def load_eco_lookup() -> dict:
    """{4-field FEN: {"eco": "B10", "name": "..."}}, same cache tree_viz.py builds."""
    if not os.path.exists(ECO_CACHE_PATH):
        return {}
    with open(ECO_CACHE_PATH) as f:
        return json.load(f)


def derive_eco_from_moves(pgn_text: str, eco_lookup: dict) -> str | None:
    """Replay the game and return the ECO code for the deepest matching position.

    Mirrors tree_viz.py's _annotate_game_opening -- needed because Lichess PGNs
    carry no [ECO] header at all, unlike Chess.com's.
    """
    if not ingest.HAVE_CHESS or not eco_lookup:
        return None
    try:
        game = ingest.chess.pgn.read_game(io.StringIO(pgn_text))
        if game is None:
            return None
        board = game.board()
        best_eco = None
        for move in game.mainline_moves():
            board.push(move)
            key = " ".join(board.fen().split()[:4])
            if key in eco_lookup:
                best_eco = eco_lookup[key]["eco"]
        return best_eco
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Bucket-relative paths (mirrors ingest.py's RAW_CHESSCOM_DIR pattern)
# ---------------------------------------------------------------------------

def raw_lichess_dir() -> str:
    return os.path.join(ingest.DATA_DIR, "raw", "lichess")


# ---------------------------------------------------------------------------
# Lichess fetcher
# ---------------------------------------------------------------------------

def _headers(username: str) -> dict:
    headers = dict(HEADERS_BASE)
    headers["User-Agent"] = f"chess-rag-ingest/1.0 (personal use; lichess-username={username})"
    if LICHESS_TOKEN:
        headers["Authorization"] = f"Bearer {LICHESS_TOKEN}"
    return headers


def fetch_lichess_games_pgn(username: str, max_games: int, since_ms: int | None = None) -> str:
    """GET https://lichess.org/api/games/user/{username} -> concatenated PGN text."""
    params = {"max": max_games, "sort": "dateDesc", "evals": "false", "clocks": "false"}
    if since_ms is not None:
        params["since"] = since_ms

    resp = requests.get(
        f"https://lichess.org/api/games/user/{username}",
        headers=_headers(username),
        params=params,
        timeout=60,
    )
    if resp.status_code == 404:
        raise SystemExit(f"User '{username}' not found on Lichess.")
    resp.raise_for_status()
    return resp.text


def split_pgns(blob: str) -> list[str]:
    """Split a concatenated multi-game PGN blob into individual game strings."""
    return [g.strip() for g in GAME_START_RE.split(blob.strip()) if g.strip()]


# ---------------------------------------------------------------------------
# PGN -> annotated PGN
# ---------------------------------------------------------------------------

def extract_lichess_game_id(pgn: str) -> str | None:
    gid = ingest.extract_header(pgn, "GameId")
    if gid:
        return gid
    site = ingest.extract_header(pgn, "Site") or ""
    m = re.search(r"lichess\.org/([A-Za-z0-9]{8})", site)
    return m.group(1) if m else None


def utc_ms(pgn: str) -> int | None:
    date, time_ = ingest.extract_header(pgn, "UTCDate"), ingest.extract_header(pgn, "UTCTime")
    if not (date and time_):
        return None
    try:
        dt = datetime.strptime(f"{date} {time_}", "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def build_annotated_pgn(pgn: str, my_username: str, eco_lookup: dict) -> str:
    """
    Add the same metadata headers ingest.py's Chess.com pipeline injects, so
    tree_viz/report.py treat both sources uniformly.

    Added headers: Source, MyColor, MyResult, OpponentUsername, ECO (derived
    via move-replay -- Lichess PGNs carry no native [ECO] header)
    """
    white = ingest.extract_header(pgn, "White") or ""
    black = ingest.extract_header(pgn, "Black") or ""
    result = ingest.extract_header(pgn, "Result") or "*"

    my_color = "white" if my_username.lower() == white.lower() else "black"
    opponent = black if my_color == "white" else white

    if result == "1-0":
        my_result = "win" if my_color == "white" else "loss"
    elif result == "0-1":
        my_result = "win" if my_color == "black" else "loss"
    elif result == "1/2-1/2":
        my_result = "draw"
    else:
        my_result = "unknown"

    extra = {
        "Source": "lichess",
        "MyColor": my_color,
        "MyResult": my_result,
        "OpponentUsername": opponent or "?",
    }
    eco = derive_eco_from_moves(pgn, eco_lookup)
    if eco:
        extra["ECO"] = eco
    return ingest.inject_headers(pgn, extra)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def save_raw_pgn(game_id: str, pgn: str) -> None:
    d = raw_lichess_dir()
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{game_id}.pgn"), "w") as f:
        f.write(pgn)


def load_existing_game_ids() -> set[str]:
    d = raw_lichess_dir()
    if not os.path.exists(d):
        return set()
    return {f[:-4] for f in os.listdir(d) if f.endswith(".pgn")}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest recent Lichess games into a per-user bucket"
    )
    parser.add_argument(
        "username", nargs="?", help="Lichess username "
        "(optional when running inside an existing bucket folder)",
    )
    parser.add_argument(
        "--max", type=int, default=None, metavar="N",
        help="Max games to fetch (default: 100)",
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Ignore last_fetched_at and re-fetch from scratch",
    )
    parser.add_argument(
        "--depth", type=int, default=15, metavar="D",
        help="Stockfish analysis depth (default: 15)",
    )
    parser.add_argument(
        "--no-analyze", action="store_true",
        help="Skip Stockfish annotation of fetched games",
    )
    parser.add_argument(
        "--analyze-all", action="store_true",
        help="Also annotate existing raw/lichess PGNs that lack analysis",
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
    in_bucket = os.path.basename(os.path.dirname(ingest.HERE)) == "data"
    if in_bucket:
        ingest.use_bucket(ingest.HERE)
    else:
        if not args.username:
            parser.error("username required (e.g. python lichess_ingest.py FirebirdBot)")
        ingest.use_bucket(os.path.join(ingest.HERE, "data", args.username.strip().lower()))

    username = (args.username or "").strip()
    max_games = args.max if args.max is not None else 100

    state = ingest.load_state()
    if not username:
        username = state.get("lichess", {}).get("username", "")
    if not username:
        parser.error("no username given and none recorded in state.json yet")

    print(f"Bucket: {ingest.DATA_DIR}")

    since_ms: int | None = None if args.full else state.get("lichess", {}).get("last_fetched_at")
    existing_ids = load_existing_game_ids()

    if since_ms:
        when = datetime.fromtimestamp(since_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        print(f"Incremental run — fetching games newer than {when} for {username}")
    else:
        print(f"{'Full' if args.full else 'First'} run — fetching up to {max_games} game(s) for {username}")

    blob = fetch_lichess_games_pgn(username, max_games=max_games, since_ms=since_ms)
    games = split_pgns(blob)
    print(f"  Retrieved {len(games)} game(s) from Lichess API")

    eco_lookup = load_eco_lookup()
    if not eco_lookup:
        print(f"  [warn] ECO cache not found at {ECO_CACHE_PATH} -- games will be saved without ECO")

    new_ids: list[str] = []
    latest_ms = since_ms or 0

    for pgn in games:
        game_id = extract_lichess_game_id(pgn)
        if not game_id or game_id in existing_ids:
            continue

        annotated = build_annotated_pgn(pgn, username, eco_lookup)
        save_raw_pgn(game_id, annotated)
        existing_ids.add(game_id)
        new_ids.append(game_id)

        ts = utc_ms(pgn)
        if ts and ts > latest_ms:
            latest_ms = ts

    print(f"  Saved {len(new_ids)} new PGN file(s) to {raw_lichess_dir()}")

    if not args.no_analyze:
        raw_dir = raw_lichess_dir()
        targets = [(gid, os.path.join(raw_dir, f"{gid}.pgn")) for gid in new_ids]
        if args.analyze_all:
            seen = set(new_ids)
            targets += [
                (gid, os.path.join(raw_dir, f"{gid}.pgn"))
                for gid in sorted(load_existing_game_ids())
                if gid not in seen
            ]
        ingest.annotate_games(targets, args.depth, parallel=args.parallel, sf_threads=args.sf_threads)

    ingest.rebuild_games_pgn()

    state.setdefault("lichess", {}).update(
        {"last_fetched_at": latest_ms, "username": username}
    )
    ingest.save_state(state)
    print(f"  State saved → {ingest.STATE_PATH}")

    ingest.copy_scripts(ingest.DATA_DIR)
    print(f"  Pipeline scripts synced → {ingest.DATA_DIR}")
    print("Done.")


if __name__ == "__main__":
    main()
