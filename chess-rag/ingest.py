#!/usr/bin/env python3
"""
Phase 1 — Ingest: pull the last 100 Chess.com games into a local PGN store.

Usage:
    python ingest.py <username>
    python ingest.py <username> --max 50

On first run:
    Walks Chess.com archives newest → oldest until max_games collected.
    Writes one annotated PGN per game to data/raw/chesscom/<game_id>.pgn.
    Writes merged, de-duplicated data/games.pgn.
    Records last_fetched_at in data/state.json.

On subsequent runs:
    Only fetches games newer than last_fetched_at, merges with existing
    raw PGNs, then re-trims to the most recent max_games total.
"""

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
RAW_CHESSCOM_DIR = os.path.join(DATA_DIR, "raw", "chesscom")
GAMES_PGN_PATH = os.path.join(DATA_DIR, "games.pgn")
STATE_PATH = os.path.join(DATA_DIR, "state.json")

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
) -> list[dict]:
    """
    Fetch up to max_games raw game dicts from Chess.com (newest first).

    Walks the archives list from most recent month backward, stopping when
    either max_games is reached or a game older than since_timestamp is seen.
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


def trim_raw_store(max_games: int) -> None:
    """Remove oldest raw PGNs beyond max_games (by numeric game ID)."""
    fnames = sorted(
        [f for f in os.listdir(RAW_CHESSCOM_DIR) if f.endswith(".pgn")],
        key=_sort_key,
    )
    excess = len(fnames) - max_games
    if excess > 0:
        for fname in fnames[:excess]:  # oldest first
            os.remove(os.path.join(RAW_CHESSCOM_DIR, fname))
        print(f"  Trimmed {excess} old game(s) to stay at {max_games} total")


def rebuild_games_pgn(max_games: int) -> None:
    """
    Rebuild data/games.pgn from all raw/chesscom PGNs.
    Sorted newest → oldest by numeric game ID. Capped at max_games.
    """
    fnames = sorted(
        [f for f in os.listdir(RAW_CHESSCOM_DIR) if f.endswith(".pgn")],
        key=_sort_key,
        reverse=True,  # newest first
    )[:max_games]

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(GAMES_PGN_PATH, "w") as out:
        for fname in fnames:
            with open(os.path.join(RAW_CHESSCOM_DIR, fname)) as f:
                out.write(f.read().strip() + "\n\n")

    print(f"  Wrote {len(fnames)} games → {GAMES_PGN_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest recent Chess.com games into local PGN store"
    )
    parser.add_argument("username", help="Chess.com username")
    parser.add_argument(
        "--max", type=int, default=100, metavar="N",
        help="Max games to keep (default: 100)",
    )
    args = parser.parse_args()

    username = args.username.strip().lower()
    max_games = args.max

    state = load_state()
    since_ts: int | None = state.get("chesscom", {}).get("last_fetched_at")
    existing_ids = load_existing_game_ids()

    if since_ts:
        when = datetime.fromtimestamp(since_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        print(f"Incremental run — fetching games newer than {when} for {username}")
    else:
        print(f"First run — fetching up to {max_games} games for {username}")

    raw_games = fetch_chesscom_games(username, max_games=max_games, since_timestamp=since_ts)
    print(f"  Retrieved {len(raw_games)} game(s) from Chess.com API")

    new_count = 0
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

        end_time = game.get("end_time", 0)
        if end_time > latest_end_time:
            latest_end_time = end_time

    print(f"  Saved {new_count} new PGN file(s) to {RAW_CHESSCOM_DIR}")

    trim_raw_store(max_games)
    rebuild_games_pgn(max_games)

    state.setdefault("chesscom", {}).update(
        {"last_fetched_at": latest_end_time, "username": username}
    )
    save_state(state)
    print(f"  State saved → {STATE_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()
