#!/usr/bin/env python3
"""
Push raw PGNs from a bucket's raw/chesscom and raw/lichess folders into the
Supabase `games` table (see the schema in the conversation that introduced
this table — RLS enabled, no anon/authenticated policies, service_role only).

Usage:
    python push_to_supabase.py data/tttstanley --username TTTstanley
    python push_to_supabase.py data/firebirdbot --username FirebirdBot
    python push_to_supabase.py data/tttstanley --username TTTstanley --dry-run

Requires environment variables (export them, or put them in chess-rag/.env):
    SUPABASE_URL              e.g. https://xxxx.supabase.co
    SUPABASE_SERVICE_ROLE_KEY the service_role key (Project Settings -> API)
                              NEVER the anon key -- RLS has no policies on
                              `games`, so only service_role can write to it.
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
BATCH_SIZE = 200


def load_dotenv(path: str) -> None:
    """Minimal .env loader (no external dependency).

    Values in this file win over already-exported shell env vars of the same
    name -- important because SUPABASE_URL/SUPABASE_KEY are common names that
    may already be exported globally (e.g. for an unrelated project).
    """
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value:
                os.environ[key] = value


def extract_header(pgn: str, key: str) -> str | None:
    m = re.search(rf'\[{re.escape(key)}\s+"([^"]*)"\]', pgn)
    return m.group(1) if m else None


def parse_elo(raw: str | None) -> int | None:
    return int(raw) if raw and raw.isdigit() else None


def parse_played_at(pgn: str) -> str | None:
    date = extract_header(pgn, "UTCDate") or extract_header(pgn, "Date")
    time_ = extract_header(pgn, "UTCTime") or "00:00:00"
    if not date or date == "????.??.??":
        return None
    try:
        dt = datetime.strptime(f"{date} {time_}", "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        return None


def my_color_and_result(white: str | None, black: str | None, result: str | None, username: str) -> tuple[str | None, str | None]:
    uname = username.lower()
    if white and white.lower() == uname:
        color = "white"
    elif black and black.lower() == uname:
        color = "black"
    else:
        return None, None

    if result == "1/2-1/2":
        return color, "draw"
    if result == "1-0":
        return color, "win" if color == "white" else "loss"
    if result == "0-1":
        return color, "loss" if color == "white" else "win"
    return color, None


def pgn_to_row(pgn: str, source: str, game_id: str, username: str) -> dict:
    white = extract_header(pgn, "White")
    black = extract_header(pgn, "Black")
    result = extract_header(pgn, "Result")
    my_color, my_result = my_color_and_result(white, black, result, username)

    return {
        "source": source,
        "game_id": game_id,
        "username": username,
        "white": white,
        "black": black,
        "white_elo": parse_elo(extract_header(pgn, "WhiteElo")),
        "black_elo": parse_elo(extract_header(pgn, "BlackElo")),
        "result": result,
        "my_color": my_color,
        "my_result": my_result,
        "eco": extract_header(pgn, "ECO"),
        "time_control": extract_header(pgn, "TimeControl"),
        "termination": extract_header(pgn, "Termination"),
        "played_at": parse_played_at(pgn),
        "pgn": pgn,
    }


def collect_rows(bucket_dir: str, username: str) -> list[dict]:
    rows = []
    for source, subdir in (("chesscom", "chesscom"), ("lichess", "lichess")):
        raw_dir = os.path.join(bucket_dir, "raw", subdir)
        if not os.path.isdir(raw_dir):
            continue
        for name in sorted(os.listdir(raw_dir)):
            if not name.endswith(".pgn"):
                continue
            game_id = name[:-4]
            with open(os.path.join(raw_dir, name)) as f:
                pgn = f.read()
            rows.append(pgn_to_row(pgn, source, game_id, username))
    return rows


def push_rows(rows: list[dict], url: str, key: str) -> None:
    endpoint = f"{url.rstrip('/')}/rest/v1/games"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    params = {"on_conflict": "source,game_id"}

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        r = requests.post(endpoint, headers=headers, params=params, json=batch, timeout=30)
        if not r.ok:
            print(f"Batch {i // BATCH_SIZE + 1} failed ({r.status_code}): {r.text}", file=sys.stderr)
            r.raise_for_status()
        print(f"Pushed rows {i + 1}-{i + len(batch)} of {len(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bucket_dir", help="Bucket folder, e.g. data/tttstanley or data/firebirdbot")
    parser.add_argument("--username", required=True, help="The tracked player's username on that source")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print a summary, but don't push")
    args = parser.parse_args()

    load_dotenv(os.path.join(HERE, ".env"))

    bucket_dir = args.bucket_dir if os.path.isabs(args.bucket_dir) else os.path.join(HERE, args.bucket_dir)
    if not os.path.isdir(bucket_dir):
        sys.exit(f"No such bucket directory: {bucket_dir}")

    rows = collect_rows(bucket_dir, args.username)
    if not rows:
        sys.exit(f"No PGNs found under {bucket_dir}/raw/{{chesscom,lichess}}")

    print(f"Parsed {len(rows)} games from {bucket_dir}")
    if args.dry_run:
        print("Sample row:", {k: (v[:60] + "..." if k == "pgn" and v else v) for k, v in rows[0].items()})
        print("Dry run -- nothing pushed.")
        return

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (env vars or chess-rag/.env)")

    push_rows(rows, url, key)
    print("Done.")


if __name__ == "__main__":
    main()
