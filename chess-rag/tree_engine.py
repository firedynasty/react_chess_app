#!/usr/bin/env python3
"""
Phase 2 — Position tree engine.

Parses data/games.pgn, builds a transposition-aware SQLite position tree,
and exposes:
    get_children(conn, position_key) → moves with win/draw/loss stats
    get_path(conn, moves, start_fen) → node list along a line

Build the tree:
    python tree_engine.py

Query the tree:
    python tree_engine.py --query e4 e5 Nf3

Options:
    --pgn  PATH   Input PGN (default: data/games.pgn)
    --db   PATH   SQLite output (default: data/tree.sqlite)
    --query MOVE… Walk the tree along these moves and print children at each step
"""

import argparse
import re
import sqlite3
from pathlib import Path

import chess
import chess.pgn

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).parent
DEFAULT_PGN = HERE / "data" / "games.pgn"
DEFAULT_DB = HERE / "data" / "tree.sqlite"

# ---------------------------------------------------------------------------
# Schema  (as specified)
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    position_key TEXT PRIMARY KEY,
    fen          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edges (
    position_key      TEXT    NOT NULL,
    move_uci          TEXT    NOT NULL,
    move_san          TEXT    NOT NULL,
    next_position_key TEXT    NOT NULL,
    game_id           TEXT    NOT NULL,
    my_color          TEXT    NOT NULL,
    result            TEXT    NOT NULL,
    ply               INTEGER NOT NULL,
    PRIMARY KEY (position_key, move_uci, game_id)
);

CREATE INDEX IF NOT EXISTS idx_edges_position ON edges(position_key);
"""


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def open_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def _position_key(board: chess.Board) -> str:
    """Stable transposition key: FEN minus the halfmove/fullmove counters.

    The first four FEN fields (piece placement, side to move, castling rights,
    en-passant square) uniquely identify a chess position for repetition /
    transposition purposes. Stripping the counters means two games that reach
    the same position via different move orders produce the same key.
    """
    parts = board.fen().split()
    return " ".join(parts[:4])


# ---------------------------------------------------------------------------
# PGN helpers
# ---------------------------------------------------------------------------

def _game_id(game: chess.pgn.Game) -> str:
    """Extract numeric game ID from the Link or Site PGN header."""
    for key in ("Link", "Site"):
        url = game.headers.get(key, "")
        m = re.search(r"/game/(?:live|daily)/(\d+)", url)
        if m:
            return m.group(1)
    # Fallback: stable string from metadata
    return (
        f"{game.headers.get('Date', '?')}"
        f"_{game.headers.get('White', '?')}"
        f"_{game.headers.get('Black', '?')}"
    )


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_tree(pgn_path: Path, db_path: Path) -> None:
    """
    Parse every game in pgn_path and populate the position tree.

    Transposition check: INSERT OR IGNORE on positions means two games that
    reach the same position via different move orders produce ONE row, not two.
    """
    conn = open_db(db_path)
    cur = conn.cursor()

    game_count = 0
    edge_count = 0

    with open(pgn_path) as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            gid = _game_id(game)
            my_color = game.headers.get("MyColor", "unknown").lower()
            result = game.headers.get("Result", "*")

            board = game.board()

            for ply, move in enumerate(game.mainline_moves()):
                pk = _position_key(board)
                fen_before = board.fen()
                san = board.san(move)
                uci = move.uci()

                board.push(move)
                npk = _position_key(board)

                cur.execute(
                    "INSERT OR IGNORE INTO positions(position_key, fen) VALUES (?, ?)",
                    (pk, fen_before),
                )
                cur.execute(
                    "INSERT OR IGNORE INTO positions(position_key, fen) VALUES (?, ?)",
                    (npk, board.fen()),
                )
                cur.execute(
                    """
                    INSERT OR IGNORE INTO edges
                        (position_key, move_uci, move_san, next_position_key,
                         game_id, my_color, result, ply)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (pk, uci, san, npk, gid, my_color, result, ply),
                )
                edge_count += cur.rowcount

            game_count += 1
            if game_count % 20 == 0:
                conn.commit()
                print(f"  {game_count} games, {edge_count} edges…")

    conn.commit()
    conn.close()
    print(f"Built: {game_count} games, {edge_count} edges → {db_path}")


# ---------------------------------------------------------------------------
# Query API
# ---------------------------------------------------------------------------

def get_children(conn: sqlite3.Connection, pk: str) -> list[dict]:
    """
    Return every move ever played from position_key pk, with stats.

    Result keys:
        move_uci, move_san, next_position_key,
        games, wins, draws, losses, game_ids (comma-separated)

    wins/draws/losses are counted from MY perspective using the MyColor
    and Result headers injected by ingest.py.
    """
    rows = conn.execute(
        """
        SELECT
            move_uci,
            move_san,
            next_position_key,
            COUNT(*)                                                        AS games,
            SUM(CASE
                    WHEN (my_color = 'white' AND result = '1-0')
                      OR (my_color = 'black' AND result = '0-1')
                    THEN 1 ELSE 0 END)                                      AS wins,
            SUM(CASE WHEN result = '1/2-1/2' THEN 1 ELSE 0 END)            AS draws,
            SUM(CASE
                    WHEN (my_color = 'white' AND result = '0-1')
                      OR (my_color = 'black' AND result = '1-0')
                    THEN 1 ELSE 0 END)                                      AS losses,
            GROUP_CONCAT(game_id)                                           AS game_ids
        FROM edges
        WHERE position_key = ?
        GROUP BY move_uci, move_san, next_position_key
        ORDER BY games DESC
        """,
        (pk,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_path(
    conn: sqlite3.Connection,
    moves: list[str] | None = None,
    start_fen: str | None = None,
) -> list[dict]:
    """
    Walk from a starting position along a move sequence and return each node.

    Args:
        moves:      SAN or UCI strings, e.g. ["e4", "e5", "Nf3"].
        start_fen:  Starting FEN (omit for the standard starting position).

    Returns:
        List of dicts (one per ply, including the start):
            ply, position_key, fen, move (None for start), children_count
    """
    board = chess.Board(start_fen) if start_fen else chess.Board()
    path: list[dict] = []

    def _node(ply: int, move_str: str | None) -> dict:
        pk = _position_key(board)
        n = conn.execute(
            "SELECT COUNT(DISTINCT move_uci) FROM edges WHERE position_key = ?",
            (pk,),
        ).fetchone()[0]
        return {"ply": ply, "position_key": pk, "fen": board.fen(), "move": move_str, "children_count": n}

    path.append(_node(0, None))

    for i, move_str in enumerate(moves or []):
        try:
            move = board.parse_san(move_str)
        except Exception:
            try:
                move = chess.Move.from_uci(move_str)
                if move not in board.legal_moves:
                    raise ValueError("illegal")
            except Exception:
                print(f"  [warn] Cannot parse '{move_str}' at ply {i + 1} — stopping")
                break
        board.push(move)
        path.append(_node(i + 1, move_str))

    return path


# ---------------------------------------------------------------------------
# CLI display
# ---------------------------------------------------------------------------

def _print_children(children: list[dict], label: str = "") -> None:
    if label:
        print(f"\n{label}")
    if not children:
        print("  (no recorded games from this position)")
        return
    for c in children:
        g = c["games"]
        w, d, l = c["wins"], c["draws"], c["losses"]
        pct = f"{100 * w // g}%" if g else "-"
        ids = (c["game_ids"] or "").split(",")
        snippet = ", ".join(ids[:3]) + ("…" if len(ids) > 3 else "")
        print(f"  {c['move_san']:6s}  {g:3d}g  +{w}={d}-{l}  ({pct} wins)  [{snippet}]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build / query the chess position tree")
    parser.add_argument("--pgn", default=str(DEFAULT_PGN))
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument(
        "--query", nargs="*", metavar="MOVE",
        help="Print tree stats along this move sequence",
    )
    args = parser.parse_args()

    pgn_path = Path(args.pgn)
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if args.query is not None:
        if not db_path.exists():
            raise SystemExit(f"No database at {db_path} — build it first (run without --query).")
        conn = open_db(db_path)
        path = get_path(conn, moves=args.query)
        for node in path:
            label = f"After {node['move']} (ply {node['ply']})" if node["move"] else "Starting position"
            _print_children(get_children(conn, node["position_key"]), label=label)
        conn.close()
    else:
        if not pgn_path.exists():
            raise SystemExit(f"PGN not found: {pgn_path} — run ingest.py first.")
        print(f"Building tree: {pgn_path} → {db_path}")
        build_tree(pgn_path, db_path)


if __name__ == "__main__":
    main()
