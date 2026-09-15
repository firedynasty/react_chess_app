#!/usr/bin/env python3
"""
Prototype: AI game report for a group of games from the same opening position.

Usage (from inside a bucket folder, data/<key>/):
    python report.py <game_id> [game_id ...]
    python report.py 164380092682 171996841806 172074667356
    python report.py --position "d4 d5 e3 Nc6 Bd3 Nf6 f4"

Usage (from chess-rag/ — point at a bucket with --key):
    python report.py --key tttstanley --position "d4 d5"

Output:
    <bucket>/reports/<timestamp>_<position>/
        run_meta.json      — position, games, timestamp
        <game_id>.md       — per-game report
        comparison.md      — cross-game comparison (wins vs losses)
        report.html        — self-contained viewer (shareable on its own)

Quantitative stats export (no OpenAI key needed, runs over every game in the bucket):
    python report.py --key tttstanley --stats-csv
    python report.py --key tttstanley --stats-csv --blunder-cp 150

Output:
    <bucket>/stats_games.csv     — one row per game: per-phase (opening/middlegame/
                                    endgame) avg centipawn loss, time-management
                                    aggregates, blunder count
    <bucket>/stats_blunders.csv  — one row per detected mistake/blunder: phase,
                                    centipawn loss, severity, a best-effort category
                                    (hanging_piece / missed_tactic / positional_misjudgment /
                                    endgame_technique), and whether it happened in time trouble
    Import either CSV into Google Sheets via File > Import > Upload.

Requires:
    pip install openai python-chess
    export OPENAI_API_KEY=sk-...   (not needed for --stats-csv)
"""

import argparse
import csv
import json
import math
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    sys.exit("Missing: pip install openai")

try:
    import chess
    import chess.pgn
    import io
except ImportError:
    sys.exit("Missing: pip install python-chess")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).parent
# Reassigned in main() from the resolved bucket:
RAW_DIR = HERE / "data" / "raw" / "chesscom"
DB_PATH = HERE / "data" / "tree.sqlite"
REPORTS_DIR = HERE / "reports"


def resolve_bucket(key: str | None) -> Path:
    """Bucket folder for this run.

    A key resolves to data/<key>/ next to this script; without a key, a
    script copied inside a bucket (data/<key>/) uses its own folder.
    """
    if key:
        return HERE / "data" / key.strip().lower()
    if HERE.parent.name == "data":
        return HERE
    raise SystemExit(
        "Pass --key <name> (e.g. python report.py --key tttstanley …) "
        "or run from inside a bucket folder (data/<key>/)."
    )

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_knowledge() -> str:
    """Load chess_knowledge.txt as plain context string.

    Walks up from this script's location so it works both from chess-rag/
    and from a copied script inside a bucket (data/<key>/).
    """
    for base in (HERE, *HERE.parents):
        path = base / "chess_knowledge.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
    print("[warn] chess_knowledge.txt not found — proceeding without theory context")
    return ""


def pgn_header(pgn: str, key: str) -> str:
    m = re.search(rf'\[{re.escape(key)}\s+"([^"]*)"\]', pgn)
    return m.group(1) if m else ""


def load_pgn(game_id: str) -> str | None:
    path = RAW_DIR / f"{game_id}.pgn"
    if not path.exists():
        print(f"[warn] PGN not found: {path}")
        return None
    return path.read_text(encoding="utf-8")


def game_summary(pgn: str, game_id: str) -> dict:
    """Extract key metadata from a PGN string."""
    return {
        "id":        game_id,
        "white":     pgn_header(pgn, "White"),
        "black":     pgn_header(pgn, "Black"),
        "result":    pgn_header(pgn, "Result"),
        "date":      pgn_header(pgn, "Date") or pgn_header(pgn, "EndDate"),
        "my_color":  pgn_header(pgn, "MyColor"),
        "my_result": pgn_header(pgn, "MyResult"),
        "opening":   pgn_header(pgn, "Opening") or pgn_header(pgn, "ECO"),
        "time_ctrl": pgn_header(pgn, "TimeControl"),
        "url":       pgn_header(pgn, "Link") or pgn_header(pgn, "Site"),
        "pgn":       pgn,
    }


def pgn_moves_only(pgn: str) -> str:
    """Strip headers, keep just the move text."""
    lines = pgn.strip().split("\n")
    move_lines = [l for l in lines if l and not l.startswith("[")]
    return " ".join(move_lines).strip()


# ---------------------------------------------------------------------------
# Tree stats
# ---------------------------------------------------------------------------

def _position_key(board: chess.Board) -> str:
    parts = board.fen().split()
    return " ".join(parts[:4])


def tree_stats_along_path(moves: list[str]) -> list[dict]:
    """
    Walk the position tree along `moves` (SAN strings) and return
    stats at each position: what you played and your historical W/D/L there.
    """
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    board = chess.Board()
    stats = []

    for i, san in enumerate(moves):
        pk = _position_key(board)

        # What did you play from here across all games?
        rows = conn.execute(
            """
            SELECT move_san, COUNT(*) AS g,
                   SUM(CASE WHEN (my_color='white' AND result='1-0')
                              OR (my_color='black' AND result='0-1') THEN 1 ELSE 0 END) AS w,
                   SUM(CASE WHEN result='1/2-1/2' THEN 1 ELSE 0 END) AS d,
                   SUM(CASE WHEN (my_color='white' AND result='0-1')
                              OR (my_color='black' AND result='1-0') THEN 1 ELSE 0 END) AS l
            FROM edges WHERE position_key=?
            GROUP BY move_san ORDER BY g DESC
            """, (pk,)
        ).fetchall()

        stats.append({
            "ply": i + 1,
            "move": san,
            "position_key": pk,
            "all_moves": [dict(r) for r in rows],
        })

        try:
            board.push_san(san)
        except Exception:
            break

    conn.close()
    return stats


def format_tree_stats(stats: list[dict]) -> str:
    if not stats:
        return "No tree stats available."
    lines = []
    for s in stats:
        moves_str = "  |  ".join(
            f"{r['move_san']} ({r['g']}g +{r['w']}={r['d']}-{r['l']})"
            for r in s["all_moves"][:4]
        )
        lines.append(f"  Ply {s['ply']} ({s['move']}): {moves_str or 'no data'}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Games that passed through a position
# ---------------------------------------------------------------------------

def game_ids_for_position(moves: list[str]) -> list[str]:
    """Return game IDs that went through the position after `moves`."""
    if not DB_PATH.exists():
        return []
    board = chess.Board()
    for san in moves:
        try:
            board.push_san(san)
        except Exception:
            break
    pk = _position_key(board)

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT DISTINCT game_id FROM edges WHERE position_key=?", (pk,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a direct chess analyst. Be specific and concrete.
When analyzing games:
- Identify the exact moves where the advantage shifted
- Explain WHY those moves were good or bad (principles, not just engine numbers)
- Compare wins vs losses to find the pattern
- Keep it focused — no filler, no preamble
"""


def build_single_game_prompt(game: dict, tree_stats: list[dict], knowledge: str) -> str:
    moves = pgn_moves_only(game["pgn"])
    stats_str = format_tree_stats(tree_stats)
    my_color = game["my_color"] or "unknown"
    my_result = game["my_result"] or "unknown"

    ctx = ""
    if knowledge:
        ctx = f"""
## Chess Theory Reference
{knowledge[:6000]}
---
"""

    return f"""{ctx}
## Game to Analyze
- Players: {game['white']} (White) vs {game['black']} (Black)
- I played: {my_color} | Result for me: {my_result}
- Date: {game['date']} | Time control: {game['time_ctrl']}
- URL: {game['url']}

## Moves
{moves}

## My Historical Stats at Key Positions in This Game
{stats_str}

---
Analyze this game. Focus on:
1. The opening — did I follow good principles or deviate badly?
2. The critical turning point — what specific move(s) decided the game?
3. What I should have played instead
4. One concrete thing to improve or study based on this game
"""


def build_comparison_prompt(games: list[dict], knowledge: str) -> str:
    wins  = [g for g in games if g["my_result"] == "win"]
    losses = [g for g in games if g["my_result"] == "loss"]
    draws  = [g for g in games if g["my_result"] == "draw"]

    def game_block(g: dict) -> str:
        return (
            f"### {'Win' if g['my_result']=='win' else 'Loss' if g['my_result']=='loss' else 'Draw'}"
            f" vs {g['black'] if g['my_color']=='white' else g['white']}"
            f" ({g['date']})\n"
            f"{pgn_moves_only(g['pgn'])}\n"
        )

    all_blocks = "\n".join(game_block(g) for g in games)

    ctx = ""
    if knowledge:
        ctx = f"## Chess Theory Reference\n{knowledge[:4000]}\n---\n"

    return f"""{ctx}
## Games to Compare ({len(games)} total: {len(wins)} wins, {len(losses)} losses, {len(draws)} draws)
All games share the same opening position.

{all_blocks}

---
Compare these games and answer:
1. What did I do DIFFERENTLY in the wins vs the losses after the shared opening moves?
2. Is there a recurring mistake in the losses (specific move, pawn structure, piece placement)?
3. What pattern in the wins can I replicate?
4. One concrete recommendation: what should I play or avoid in this position?
"""


# ---------------------------------------------------------------------------
# OpenAI call
# ---------------------------------------------------------------------------

def call_openai(client: OpenAI, prompt: str, model: str = "gpt-4o") -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=1500,
    )
    return resp.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Phase / time-management / blunder stats → CSV (quantitative, no OpenAI call)
#
# Reads the %eval and %clk annotations already embedded in every PGN (written
# by annotate.py) and computes, per game: average centipawn loss split by
# opening/middlegame/endgame, time-management aggregates, and a list of
# individual mistakes/blunders with a best-effort category tag. Output is two
# CSVs meant to be imported into Google Sheets (File > Import) for pivoting —
# this module never calls an LLM, so it's free and fast to run over an entire
# bucket's games.
# ---------------------------------------------------------------------------

PIECE_VALUES = {chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}

# Endgame heuristic: once combined non-pawn material (both sides) drops to
# this or below, treat the game as being in the endgame from that ply on.
# Roughly "queens are off plus a couple of minor pieces traded" — an
# approximation, not a formal definition.
ENDGAME_MATERIAL_THRESHOLD = 14

# (centipawn-loss-on-this-move >= threshold, severity label), checked in order
BLUNDER_TIERS = [(300, "blunder"), (100, "mistake"), (50, "inaccuracy")]

_EVAL_MATE_RE = re.compile(r"\[%eval #(-?\d+)\]")
_EVAL_CP_RE   = re.compile(r"\[%eval (-?[\d.]+)\]")
_CLK_RE       = re.compile(r"\[%clk (\d+):(\d{2}):(\d{2}(?:\.\d+)?)\]")


def _non_pawn_material(board: "chess.Board") -> int:
    """Combined non-pawn material for both sides (kings/pawns excluded)."""
    total = 0
    for piece_type, val in PIECE_VALUES.items():
        total += val * len(board.pieces(piece_type, chess.WHITE))
        total += val * len(board.pieces(piece_type, chess.BLACK))
    return total


def _side_material(board: "chess.Board", white: bool) -> int:
    color = chess.WHITE if white else chess.BLACK
    return sum(val * len(board.pieces(pt, color)) for pt, val in PIECE_VALUES.items())


def _parse_eval_white_persp(comment: str) -> float | None:
    """Centipawns from White's perspective, clipped to +-1000 (10 pawns); mate scores map to +-1000."""
    m = _EVAL_MATE_RE.search(comment)
    if m:
        return math.copysign(1000.0, int(m.group(1)))
    m = _EVAL_CP_RE.search(comment)
    if m:
        return max(-1000.0, min(1000.0, float(m.group(1)) * 100))
    return None


def _parse_clock_seconds(comment: str) -> float | None:
    m = _CLK_RE.search(comment)
    if not m:
        return None
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def _parse_time_control(tc: str) -> tuple[float, float]:
    """'180+2' -> (180.0, 2.0). Unparseable/daily/unknown controls fall back to (300, 0)."""
    if not tc or tc in ("-", "?") or "/" in tc:
        return 300.0, 0.0
    base = tc.split("+")[0]
    inc = tc.split("+")[1] if "+" in tc else "0"
    try:
        return float(base), float(inc)
    except ValueError:
        return 300.0, 0.0


def analyze_game_for_stats(
    game_id: str, pgn_text: str, eco_lookup: dict, blunder_cp: int = 100
) -> tuple[dict, list[dict]]:
    """
    Returns (game_row, blunder_rows) for one game.

    game_row: one row summarizing the game — per-phase avg centipawn loss,
      time-management aggregates, blunder count.
    blunder_rows: one row per move by MY_COLOR whose centipawn loss cleared
      the lowest BLUNDER_TIERS threshold, with a best-effort category tag.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return {}, []

    my_color = pgn_header(pgn_text, "MyColor")
    my_result = pgn_header(pgn_text, "MyResult")
    players = f"{pgn_header(pgn_text, 'White')} vs {pgn_header(pgn_text, 'Black')}"
    date = pgn_header(pgn_text, "Date") or pgn_header(pgn_text, "EndDate")
    tc = pgn_header(pgn_text, "TimeControl")
    base_secs, inc_secs = _parse_time_control(tc)
    my_is_white = my_color == "white"

    _, _, opening_sans, _ = _annotate_game_opening(pgn_text, eco_lookup)
    opening_ply_end = len(opening_sans)  # plies 1..opening_ply_end count as "opening"

    # First pass: replay the mainline once, capturing per-ply state.
    records = []
    board = game.board()
    for node in game.mainline():
        move = node.move
        mover_is_white = board.turn
        san = board.san(move)
        board.push(move)
        records.append({
            "san": san,
            "mover_is_white": mover_is_white,
            "comment": node.comment or "",
            "board_after": board.copy(stack=False),
        })

    # Second pass: derive cp-loss / phase / time / blunders, with 1-ply lookahead
    # (to detect "my move immediately lost material to the opponent's reply").
    last_clock = {True: base_secs, False: base_secs}
    prev_eval_white = 0.0
    phase_loss = {"opening": [], "middlegame": [], "endgame": []}
    my_think_times: list[float] = []
    my_time_trouble_moves = 0
    blunder_rows: list[dict] = []

    for i, rec in enumerate(records):
        ply = i + 1
        mover_is_white = rec["mover_is_white"]
        is_my_move = mover_is_white == my_is_white
        eval_white = _parse_eval_white_persp(rec["comment"])
        clk = _parse_clock_seconds(rec["comment"])
        non_pawn_mat = _non_pawn_material(rec["board_after"])
        phase = (
            "opening" if ply <= opening_ply_end
            else "endgame" if non_pawn_mat <= ENDGAME_MATERIAL_THRESHOLD
            else "middlegame"
        )

        in_time_trouble = False
        if clk is not None:
            prev = last_clock[mover_is_white]
            think_time = max(0.0, prev + inc_secs - clk)
            last_clock[mover_is_white] = clk
            in_time_trouble = clk < max(10.0, 0.1 * base_secs)
            if is_my_move:
                my_think_times.append(think_time)
                if in_time_trouble:
                    my_time_trouble_moves += 1

        cp_loss = None
        if eval_white is not None:
            mover_before = prev_eval_white if mover_is_white else -prev_eval_white
            mover_after  = eval_white if mover_is_white else -eval_white
            cp_loss = max(0.0, mover_before - mover_after)

        if is_my_move and cp_loss is not None:
            phase_loss[phase].append(cp_loss)

            severity = next((label for tier_cp, label in BLUNDER_TIERS if cp_loss >= tier_cp), None)
            if severity and cp_loss >= blunder_cp:
                # Did the opponent immediately capture material on their very next move?
                my_mat_now = _side_material(rec["board_after"], my_is_white)
                hung_piece = False
                if i + 1 < len(records):
                    my_mat_after_reply = _side_material(records[i + 1]["board_after"], my_is_white)
                    hung_piece = (my_mat_now - my_mat_after_reply) >= 3

                if hung_piece:
                    category = "hanging_piece"
                elif cp_loss >= 400:
                    category = "missed_tactic"
                elif phase == "endgame":
                    category = "endgame_technique"
                else:
                    category = "positional_misjudgment"

                blunder_rows.append({
                    "game_id": game_id,
                    "players": players,
                    "date": date,
                    "ply": ply,
                    "move": rec["san"],
                    "phase": phase,
                    "cp_loss": round(cp_loss, 1),
                    "severity": severity,
                    "category": category,
                    "clock_remaining_s": round(clk, 1) if clk is not None else "",
                    "in_time_trouble": in_time_trouble,
                    "my_color": my_color,
                })

        if eval_white is not None:
            prev_eval_white = eval_white

    def _avg(lst: list[float]) -> float | str:
        return round(sum(lst) / len(lst), 1) if lst else ""

    game_row = {
        "game_id": game_id,
        "players": players,
        "date": date,
        "my_color": my_color,
        "my_result": my_result,
        "tc": tc,
        "opening_cp_loss_avg": _avg(phase_loss["opening"]),
        "middlegame_cp_loss_avg": _avg(phase_loss["middlegame"]),
        "endgame_cp_loss_avg": _avg(phase_loss["endgame"]),
        "avg_think_time_s": _avg(my_think_times),
        "time_trouble_moves": my_time_trouble_moves,
        "blunder_count": len(blunder_rows),
        "total_plies": len(records),
    }
    return game_row, blunder_rows


def _load_eco_lookup() -> dict:
    """Lazily import tree_viz.py (same directory) and return its ECO position lookup."""
    global load_eco_data, _annotate_game_opening
    sys.path.insert(0, str(HERE))
    from tree_viz import load_eco_data, _annotate_game_opening
    return load_eco_data()


def write_stats_csvs(out_dir: Path, game_rows: list[dict], blunder_rows_all: list[dict]) -> None:
    """Write stats_games.csv / stats_blunders.csv into `out_dir` (skips a file if its rows are empty)."""
    games_csv = out_dir / "stats_games.csv"
    blunders_csv = out_dir / "stats_blunders.csv"

    if game_rows:
        with open(games_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(game_rows[0].keys()))
            w.writeheader()
            w.writerows(game_rows)
        print(f"Wrote {len(game_rows)} game row(s) -> {games_csv}")
    if blunder_rows_all:
        with open(blunders_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(blunder_rows_all[0].keys()))
            w.writeheader()
            w.writerows(blunder_rows_all)
        print(f"Wrote {len(blunder_rows_all)} blunder row(s) -> {blunders_csv}")


def run_stats_export(bucket: Path, blunder_cp: int = 100) -> None:
    """Compute phase/time/blunder stats for every game in `bucket` and write two CSVs."""
    eco_lookup = _load_eco_lookup()
    raw_dir = bucket / "raw" / "chesscom"
    pgn_files = sorted(raw_dir.glob("*.pgn"))
    if not pgn_files:
        sys.exit(f"No PGNs found in {raw_dir}")

    print(f"Analyzing {len(pgn_files)} games in {raw_dir} for phase/time/blunder stats...")
    game_rows, blunder_rows_all = [], []
    for i, path in enumerate(pgn_files, 1):
        gid = path.stem
        text = path.read_text(encoding="utf-8")
        try:
            game_row, blunder_rows = analyze_game_for_stats(gid, text, eco_lookup, blunder_cp)
        except Exception as e:
            print(f"  [warn] {gid}: {e}")
            continue
        if game_row:
            game_rows.append(game_row)
            blunder_rows_all.extend(blunder_rows)
        if i % 250 == 0:
            print(f"  ...{i}/{len(pgn_files)}")

    print()
    write_stats_csvs(bucket, game_rows, blunder_rows_all)
    print("Import either file into Google Sheets via File > Import > Upload.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    global RAW_DIR, DB_PATH, REPORTS_DIR

    parser = argparse.ArgumentParser(description="Generate AI game reports")
    parser.add_argument("game_ids", nargs="*", help="Game IDs to analyze")
    parser.add_argument(
        "--key", metavar="NAME",
        help="Bucket key (data/<name>/); not needed when running inside a bucket folder",
    )
    parser.add_argument(
        "--position", "-p", metavar="MOVES",
        help='SAN moves to auto-find all games (e.g. "d4 d5 e3 Nc6 Bd3 Nf6 f4")',
    )
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model (default: gpt-4o)")
    parser.add_argument(
        "--stats-csv", action="store_true",
        help="Skip AI reports; compute phase/time/blunder stats for EVERY game in the "
             "bucket and write stats_games.csv + stats_blunders.csv for Google Sheets import. "
             "No OpenAI key needed.",
    )
    parser.add_argument(
        "--blunder-cp", type=int, default=100, metavar="N",
        help="Centipawn-loss threshold for the 'mistake' tier and above in --stats-csv "
             "(default: 100; moves below this aren't recorded as blunder rows)",
    )
    args = parser.parse_args()

    bucket = resolve_bucket(args.key)
    RAW_DIR = bucket / "raw" / "chesscom"
    DB_PATH = bucket / "tree.sqlite"
    REPORTS_DIR = bucket / "reports"

    if args.stats_csv:
        run_stats_export(bucket, blunder_cp=args.blunder_cp)
        return

    # Resolve game IDs
    game_ids = list(args.game_ids)
    if args.position:
        moves = args.position.split()
        found = game_ids_for_position(moves)
        print(f"Found {len(found)} game(s) at position: {args.position}")
        game_ids = list(dict.fromkeys(game_ids + found))  # merge, dedupe

    if not game_ids:
        sys.exit("Provide game IDs or --position MOVES")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Set OPENAI_API_KEY first")

    client = OpenAI(api_key=api_key)
    knowledge = load_knowledge()

    games = []
    for gid in game_ids:
        pgn = load_pgn(gid)
        if not pgn:
            continue
        games.append(game_summary(pgn, gid))

    if not games:
        sys.exit("No valid PGNs found")

    # ── Create run folder ──────────────────────────────────────────────────
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M")
    position_slug = args.position.replace(" ", "-") if args.position else "manual"
    # Trim slug so folder names stay readable
    position_slug = position_slug[:30]
    run_dir = REPORTS_DIR / f"{timestamp}_{position_slug}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Write run_meta.json so this folder is self-describing
    meta = {
        "generated": now.isoformat(),
        "model": args.model,
        "position_moves": args.position or "",
        "game_ids": [g["id"] for g in games],
        "games": [
            {
                "id": g["id"],
                "white": g["white"],
                "black": g["black"],
                "my_color": g["my_color"],
                "my_result": g["my_result"],
                "date": g["date"],
                "url": g["url"],
            }
            for g in games
        ],
    }
    (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nRun folder: {run_dir}")

    # ── Phase/time/blunder stats, scoped to just these games ───────────────
    eco_lookup = _load_eco_lookup()
    stat_game_rows, stat_blunder_rows = [], []
    for g in games:
        game_row, blunder_rows = analyze_game_for_stats(g["id"], g["pgn"], eco_lookup, args.blunder_cp)
        if game_row:
            stat_game_rows.append(game_row)
            stat_blunder_rows.extend(blunder_rows)
    write_stats_csvs(run_dir, stat_game_rows, stat_blunder_rows)

    print(f"\nAnalyzing {len(games)} game(s) with {args.model}...\n")

    # ── Per-game reports ───────────────────────────────────────────────────
    for g in games:
        print(f"  {g['id']}: {g['white']} vs {g['black']} ({g['my_result']} as {g['my_color']})")
        moves = pgn_moves_only(g["pgn"]).split()[:20]
        san_moves = []
        board = chess.Board()
        for m in moves:
            try:
                board.push_san(m)
                san_moves.append(m)
            except Exception:
                break

        stats = tree_stats_along_path(san_moves)
        prompt = build_single_game_prompt(g, stats, knowledge)
        report = call_openai(client, prompt, args.model)

        out_path = run_dir / f"{g['id']}.md"
        out_path.write_text(
            f"# Game Report: {g['white']} vs {g['black']}\n"
            f"**Date:** {g['date']}  |  **Result:** {g['my_result']} as {g['my_color']}\n"
            f"**URL:** {g['url']}\n\n"
            f"{report}\n\n"
            f"---\n\n## PGN\n\n```pgn\n{g['pgn'].strip()}\n```\n",
            encoding="utf-8",
        )
        print(f"    → {out_path.name}")

    # ── Comparison report (only when 2+ games) ─────────────────────────────
    if len(games) >= 2:
        print(f"\n  Generating comparison report...")
        prompt = build_comparison_prompt(games, knowledge)
        report = call_openai(client, prompt, args.model)

        ids_line = ", ".join(g["id"] for g in games)
        out_path = run_dir / "comparison.md"
        out_path.write_text(
            f"# Comparison Report\n"
            f"**Games:** {ids_line}\n"
            f"**Position:** {args.position or 'manual selection'}\n"
            f"**Generated:** {now.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"{report}\n",
            encoding="utf-8",
        )
        print(f"    → {out_path.name}")

    # ── Self-contained HTML viewer ─────────────────────────────────────────────
    print(f"\n  Generating report.html…")
    generate_run_html(run_dir, games, stat_game_rows, stat_blunder_rows)

    print(f"\nDone. All files in: {run_dir}")
    print(f"  Open:  open {run_dir / 'report.html'}")


# ---------------------------------------------------------------------------
# Run HTML viewer
# ---------------------------------------------------------------------------

RUN_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Chess Report</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #1a1a2e; color: #e0e0e0; font-family: 'Segoe UI', system-ui, sans-serif; display: flex; height: 100vh; overflow: hidden; }

/* Sidebar */
#sidebar { width: 230px; min-width: 180px; background: #16213e; border-right: 1px solid #2a2a4e; display: flex; flex-direction: column; overflow: hidden; flex-shrink: 0; }
#sidebar h1 { font-size: 0.88rem; color: #00d4ff; padding: 12px 14px 10px; letter-spacing: 0.5px; border-bottom: 1px solid #2a2a4e; }
#nav-list { flex: 1; overflow-y: auto; padding: 6px 0; }
.nav-item { padding: 8px 14px; cursor: pointer; font-size: 0.82rem; border-left: 3px solid transparent; transition: background 0.15s; }
.nav-item:hover { background: #1e2a4e; }
.nav-item.active { background: #0f3460; border-left-color: #00d4ff; color: #00d4ff; }
.nav-item.comparison { background: #16213e; border-left-color: #00d4ff; color: #00d4ff; font-weight: 700; font-size: 0.88rem; }
.nav-item.comparison:hover { background: #1e2a4e; }
.nav-item.comparison.active { background: #0f3460; }
.nav-result { font-size: 0.7rem; margin-top: 2px; }
.nav-result.win  { color: #28a745; }
.nav-result.loss { color: #dc3545; }
.nav-result.draw { color: #888; }

/* Report pane */
#report-pane { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
#toolbar { background: #0f3460; padding: 7px 16px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid #2a2a4e; flex-shrink: 0; }
#toolbar-title { color: #aaa; font-size: 0.8rem; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#play-btn { background: #163060; color: #7ec8e3; border: 1px solid #7ec8e3; padding: 4px 13px; border-radius: 4px; cursor: pointer; font-size: 0.78rem; flex-shrink: 0; }
#play-btn:hover { background: #7ec8e3; color: #1a1a2e; }
#content-area { flex: 1; overflow-y: auto; padding: 22px 28px; }
.md-body { max-width: 680px; line-height: 1.7; }
.md-body h1 { font-size: 1.3rem; color: #00d4ff; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid #2a2a4e; }
.md-body h2 { font-size: 1.05rem; color: #7ec8e3; margin: 18px 0 7px; }
.md-body h3 { font-size: 0.93rem; color: #ccc; margin: 14px 0 5px; }
.md-body p { margin-bottom: 10px; color: #ccc; }
.md-body ul, .md-body ol { padding-left: 22px; margin-bottom: 10px; color: #ccc; }
.md-body li { margin-bottom: 3px; }
.md-body strong { color: #e0e0e0; }
.md-body em { color: #bbb; }
.md-body a { color: #00d4ff; }
.md-body code { background: #2a2a3e; padding: 1px 5px; border-radius: 3px; font-size: 0.87em; }
.md-body pre { background: #1e1e30; padding: 12px 14px; border-radius: 4px; overflow-x: auto; font-size: 0.78rem; line-height: 1.5; margin-bottom: 10px; }
.md-body pre code { background: none; padding: 0; color: #bbb; }
.md-body hr { border: none; border-top: 1px solid #2a2a4e; margin: 14px 0; }
.md-body blockquote { border-left: 3px solid #00d4ff; padding-left: 12px; color: #aaa; margin: 10px 0; }

/* Board pane (right) */
#board-pane { width: 400px; flex-shrink: 0; background: #12122a; border-left: 1px solid #2a2a4e; display: none; flex-direction: column; overflow: hidden; }
#board-pane.visible { display: flex; }
#board-header { padding: 8px 10px 6px; border-bottom: 1px solid #2a2a4e; display: flex; align-items: center; gap: 6px; }
#board-caption { font-size: 0.78rem; color: #aaa; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#board-close { background: none; border: none; color: #666; font-size: 1.1rem; cursor: pointer; padding: 0 4px; line-height: 1; }
#board-close:hover { color: #ccc; }
#board-inner { padding: 10px; display: flex; flex-direction: column; align-items: center; flex: 1; overflow: hidden; }
#pgnBoard { width: 360px; height: 360px; flex-shrink: 0; }
.pgn-controls { margin-top: 8px; display: flex; gap: 6px; justify-content: center; flex-shrink: 0; }
.pgn-controls button { padding: 4px 12px; border-radius: 4px; border: 1px solid #444; background: #2a2a3a; color: #ccc; cursor: pointer; font-size: 0.95rem; }
.pgn-controls button:hover { background: #3a3a4a; }
.pgn-comment { margin-top: 6px; width: 360px; min-height: 1.1em; font-size: 12px; font-style: italic; color: #ffd700; text-align: center; flex-shrink: 0; }
.pgn-moves { margin-top: 8px; width: 100%; flex: 1; overflow-y: auto; background: #1e1e30; color: #ddd; padding: 10px 12px; font-size: 13px; line-height: 2; user-select: none; }
.pgn-moves .move-number { color: #666; }
.pgn-moves .move-san { cursor: pointer; padding: 1px 4px; border-radius: 3px; font-weight: 600; }
.pgn-moves .move-san:hover { background: #2a3a4a; }
.pgn-moves .move-san.current { background: #7a5d10; color: #fff; }
.pgn-moves .variation-container { color: #666; }
.pgn-moves .variation-move { cursor: pointer; padding: 1px 3px; border-radius: 3px; font-weight: 500; color: #aaa; }
.pgn-moves .variation-move:hover { background: #2a3a4a; }
.pgn-moves .variation-move.current { background: #7a5d10; color: #fff; }

/* Stats tables (Game Stats / Blunders tabs) */
.nav-item.stats-tab { background: #16213e; border-left-color: #ffd700; color: #ffd700; font-weight: 700; font-size: 0.85rem; }
.nav-item.stats-tab:hover { background: #1e2a4e; }
.nav-item.stats-tab.active { background: #0f3460; }
.stats-hint { font-size: 0.78rem; color: #888; margin-bottom: 10px; }
.stats-table-wrap { max-width: 100%; overflow-x: auto; }
table.stats-table { border-collapse: collapse; font-size: 0.8rem; white-space: nowrap; }
table.stats-table th, table.stats-table td { border: 1px solid #2a2a4e; padding: 5px 9px; text-align: left; }
table.stats-table th { background: #16213e; color: #7ec8e3; position: sticky; top: 0; }
table.stats-table tr:nth-child(even) td { background: #1e1e30; }
table.stats-table tr:hover td { background: #22304e; }
#copy-table-btn { background: #163060; color: #ffd700; border: 1px solid #ffd700; padding: 4px 13px; border-radius: 4px; cursor: pointer; font-size: 0.78rem; flex-shrink: 0; }
#copy-table-btn:hover { background: #ffd700; color: #1a1a2e; }
</style>
</head>
<body>

<div id="sidebar">
  <h1>Chess Report</h1>
  <div id="nav-list"></div>
</div>

<div id="report-pane">
  <div id="toolbar">
    <span id="toolbar-title">Select a report</span>
    <button id="copy-table-btn" style="display:none" onclick="copyStatsTable()">⧉ Copy table (paste into Sheets)</button>
    <button id="play-btn" style="display:none" onclick="openBoard()">▶ Play on board</button>
  </div>
  <div id="content-area">
    <div id="md-output" class="md-body"></div>
  </div>
</div>

<div id="board-pane">
  <div id="board-header">
    <span id="board-caption"></span>
    <button id="board-close" onclick="closeBoard()" title="Close board">✕</button>
  </div>
  <div id="board-inner">
    <div id="pgnBoard"></div>
    <div class="pgn-controls">
      <button onclick="pgnGoStart()">⏮</button>
      <button onclick="pgnGoPrev()">◀</button>
      <button onclick="pgnGoNext()">▶</button>
      <button onclick="pgnGoEnd()">⏭</button>
      <button onclick="pgnFlip()" title="Flip board">⇅</button>
    </div>
    <div class="pgn-comment" id="pgnComment"></div>
    <div class="pgn-moves" id="pgnMoves"></div>
  </div>
</div>

<script>
const GAMES   = __GAMES_JSON__;
const PGNS    = __PGNS_JSON__;
const REPORTS = __REPORTS_JSON__;
const STATS_GAMES    = __STATS_GAMES_JSON__;
const STATS_BLUNDERS = __STATS_BLUNDERS_JSON__;

// ── Sidebar nav ──────────────────────────────────────────────────────────────
var currentGameId = null;

function buildNav() {
  var nav = document.getElementById('nav-list');
  var html = '';
  if (REPORTS['comparison']) {
    html += '<div class="nav-item comparison" data-id="comparison" onclick="showReport(\'comparison\')">👆 Click for Comparison</div>';
  }
  if (STATS_GAMES.length) {
    html += '<div class="nav-item stats-tab" data-id="stats-games" onclick="showReport(\'stats-games\')">📊 Game Stats</div>';
  }
  if (STATS_BLUNDERS.length) {
    html += '<div class="nav-item stats-tab" data-id="stats-blunders" onclick="showReport(\'stats-blunders\')">⚠️ Blunders</div>';
  }
  GAMES.forEach(function(g) {
    var rc = g.my_result === 'win' ? 'win' : g.my_result === 'loss' ? 'loss' : 'draw';
    var rl = g.my_result === 'win' ? 'Win' : g.my_result === 'loss' ? 'Loss' : 'Draw';
    html += '<div class="nav-item" data-id="' + g.id + '" onclick="showReport(\'' + g.id + '\')">'
          + g.white + ' vs ' + g.black
          + '<div class="nav-result ' + rc + '">' + rl + ' as ' + (g.my_color||'?') + ' · ' + (g.date||'') + '</div>'
          + '</div>';
  });
  nav.innerHTML = html;
}

function showReport(id) {
  currentGameId = id;
  document.querySelectorAll('.nav-item').forEach(function(el) {
    el.classList.toggle('active', el.dataset.id === id);
  });
  document.getElementById('content-area').scrollTop = 0;
  var playBtn      = document.getElementById('play-btn');
  var copyTableBtn = document.getElementById('copy-table-btn');
  var title        = document.getElementById('toolbar-title');

  if (id === 'stats-games' || id === 'stats-blunders') {
    var rows = id === 'stats-games' ? STATS_GAMES : STATS_BLUNDERS;
    document.getElementById('md-output').innerHTML =
      '<div class="stats-hint">Click-drag to select the table, then Cmd/Ctrl+C — paste straight into a Google Sheets cell and it lands as a proper table. Or use the copy button in the toolbar.</div>'
      + renderStatsTable(rows);
    playBtn.style.display = 'none';
    copyTableBtn.style.display = '';
    title.textContent = id === 'stats-games' ? 'Game Stats' : 'Blunders';
    return;
  }

  document.getElementById('md-output').innerHTML = simpleMarkdown(REPORTS[id] || '_(no report)_');
  copyTableBtn.style.display = 'none';
  if (id !== 'comparison' && PGNS[id]) {
    playBtn.style.display = '';
    var g = PGNS[id];
    title.textContent = g.white + ' vs ' + g.black + '  (' + (g.my_result||'') + ' as ' + (g.my_color||'') + ')';
    // If board pane already open, reload with new game
    if (document.getElementById('board-pane').classList.contains('visible')) openBoard();
  } else {
    playBtn.style.display = 'none';
    title.textContent = id === 'comparison' ? 'Comparison' : id;
  }
}

// ── Stats tables (Game Stats / Blunders) ────────────────────────────────────
function escHtmlAttr(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function renderStatsTable(rows) {
  if (!rows.length) return '<p>No rows.</p>';
  var cols = Object.keys(rows[0]);
  var html = '<div class="stats-table-wrap"><table class="stats-table" id="stats-table"><thead><tr>'
    + cols.map(function(c) { return '<th>' + escHtmlAttr(c) + '</th>'; }).join('')
    + '</tr></thead><tbody>';
  rows.forEach(function(r) {
    html += '<tr>' + cols.map(function(c) { return '<td>' + escHtmlAttr(r[c]) + '</td>'; }).join('') + '</tr>';
  });
  html += '</tbody></table></div>';
  return html;
}

function copyStatsTable() {
  var table = document.getElementById('stats-table');
  if (!table) return;
  var range = document.createRange();
  range.selectNode(table);
  var sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
  try {
    document.execCommand('copy');
    var btn = document.getElementById('copy-table-btn');
    var orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(function() { btn.textContent = orig; }, 1500);
  } catch (e) {
    alert('Copy failed — select the table manually and press Cmd/Ctrl+C.');
  }
  sel.removeAllRanges();
}

// ── Markdown renderer ────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function simpleMarkdown(md) {
  var lines = md.split('\n'), out = [], inList = false, inCode = false;
  lines.forEach(function(l) {
    if (/^```/.test(l)) {
      if (inCode) { out.push('</code></pre>'); inCode = false; }
      else { if(inList){out.push('</ul>');inList=false;} out.push('<pre><code>'); inCode = true; }
      return;
    }
    if (inCode) { out.push(escHtml(l)); return; }
    if (/^### (.+)/.test(l)) { if(inList){out.push('</ul>');inList=false;} out.push('<h3>'+escHtml(l.replace(/^### /,''))+'</h3>'); return; }
    if (/^## (.+)/.test(l))  { if(inList){out.push('</ul>');inList=false;} out.push('<h2>'+escHtml(l.replace(/^## /,''))+'</h2>'); return; }
    if (/^# (.+)/.test(l))   { if(inList){out.push('</ul>');inList=false;} out.push('<h1>'+escHtml(l.replace(/^# /,''))+'</h1>'); return; }
    if (/^---+$/.test(l.trim())) { if(inList){out.push('</ul>');inList=false;} out.push('<hr>'); return; }
    if (/^[\*\-] .+/.test(l) || /^\d+\. .+/.test(l)) {
      if (!inList) { out.push('<ul>'); inList=true; }
      out.push('<li>'+inlineMd(l.replace(/^[\*\-\d\.]+\s/,''))+'</li>'); return;
    }
    if (inList) { out.push('</ul>'); inList=false; }
    if (!l.trim()) return;
    out.push('<p>'+inlineMd(l)+'</p>');
  });
  if (inList) out.push('</ul>');
  if (inCode) out.push('</code></pre>');
  return out.join('\n');
}
function inlineMd(s) {
  s = escHtml(s);
  s = s.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
  s = s.replace(/\*(.+?)\*/g,'<em>$1</em>');
  s = s.replace(/`(.+?)`/g,'<code>$1</code>');
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g,'<a href="$2" target="_blank">$1</a>');
  s = s.replace(/(https?:\/\/[^\s<"]+)/g,'<a href="$1" target="_blank">$1</a>');
  return s;
}

// ── Board pane ───────────────────────────────────────────────────────────────
var pgnBoard = null, pgnRoot = null, pgnCurrent = null, pgnNodeRegistry = {};
var pgnLibsState = 'none', pgnLibsCallbacks = [];

function ensureChessLibs(cb) {
  if (pgnLibsState === 'ready') { cb(); return; }
  pgnLibsCallbacks.push(cb);
  if (pgnLibsState === 'loading') return;
  pgnLibsState = 'loading';
  function loadScript(src, next) {
    var s = document.createElement('script'); s.src = src; s.onload = next;
    s.onerror = function() { document.getElementById('pgnMoves').textContent = 'Failed to load chess libs (internet required).'; };
    document.head.appendChild(s);
  }
  var link = document.createElement('link'); link.rel = 'stylesheet';
  link.href = 'https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.css';
  document.head.appendChild(link);
  loadScript('https://cdnjs.cloudflare.com/ajax/libs/jquery/2.2.4/jquery.min.js', function() {
    loadScript('https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.js', function() {
      loadScript('https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js', function() {
        pgnLibsState = 'ready';
        var cbs = pgnLibsCallbacks; pgnLibsCallbacks = [];
        cbs.forEach(function(f) { f(); });
      });
    });
  });
}

function openBoard() {
  if (!currentGameId || !PGNS[currentGameId]) return;
  var g = PGNS[currentGameId];
  document.getElementById('board-caption').textContent = g.white + ' vs ' + g.black + ' · ' + (g.date||'');
  document.getElementById('pgnMoves').innerHTML = 'Loading\u2026';
  document.getElementById('pgnComment').textContent = '';
  document.getElementById('board-pane').classList.add('visible');
  ensureChessLibs(function() { renderPgnText(g.pgn); });
}

function closeBoard() {
  document.getElementById('board-pane').classList.remove('visible');
  document.getElementById('play-btn').style.display = currentGameId && currentGameId !== 'comparison' && PGNS[currentGameId] ? '' : 'none';
}

function renderPgnText(text) {
  var evRe = /^\[Event /gm, m, hits = [];
  while ((m = evRe.exec(text)) !== null) hits.push(m.index);
  if (hits.length > 1) text = text.slice(0, hits[1]);
  pgnRoot = pgnParseWithVariations(text);
  if (!pgnBoard) {
    pgnBoard = Chessboard('pgnBoard', { draggable: false, position: pgnRoot.fen, pieceTheme: 'https://assets.codepen.io/1075762/{piece}.png' });
  } else {
    pgnBoard.position(pgnRoot.fen);
  }
  pgnRenderMoveTable(pgnRoot);
  pgnJumpToNode('root');
}

// PGN tokenizer
function pgnTokenize(moveText) {
  var tokens = [], current = '', inComment = false;
  for (var i = 0; i < moveText.length; i++) {
    var ch = moveText[i];
    if (ch === '{') { if (current.trim()) tokens.push(current.trim()); current = '{'; inComment = true; }
    else if (ch === '}') { current += '}'; tokens.push(current); current = ''; inComment = false; }
    else if (inComment) { current += ch; }
    else if (ch === '(' || ch === ')') { if (current.trim()) tokens.push(current.trim()); tokens.push(ch); current = ''; }
    else if (/\s/.test(ch)) { if (current.trim()) tokens.push(current.trim()); current = ''; }
    else { current += ch; }
  }
  if (current.trim()) tokens.push(current.trim());
  return tokens;
}

// PGN parser
function pgnParseWithVariations(pgnString) {
  var fenMatch = pgnString.match(/\[FEN\s+"([^"]+)"\]/);
  var startFen = fenMatch ? fenMatch[1] : 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  var moveText = pgnString.replace(/\[.*?\]/g, '').trim();
  var tokens = pgnTokenize(moveText);
  var chess = new Chess();
  try { chess.load(startFen); } catch(e) { chess.reset(); }
  var root = { san: null, fen: chess.fen(), moveNumber: 0, isBlackMove: false, comment: '', annotation: '', parent: null, children: [], depth: 0, nodeId: 'root' };
  pgnNodeRegistry = { 'root': root };
  pgnParseTokens(tokens, 0, chess, root, 0, { counter: 0 });
  return root;
}

function pgnParseTokens(tokens, startIdx, chess, parentNode, depth, ctr) {
  var i = startIdx, lastNode = parentNode, branchChess = chess;
  while (i < tokens.length) {
    var token = tokens[i];
    if (token === '(') {
      var bp = lastNode.parent || parentNode;
      var varChess = new Chess(); varChess.load(bp.fen);
      i = pgnParseTokens(tokens, i + 1, varChess, bp, depth + 1, ctr);
      continue;
    }
    if (token === ')') return i + 1;
    if (token.charAt(0) === '{') { var cmt = token.slice(1,-1).trim(); if (lastNode !== parentNode) lastNode.comment = cmt; i++; continue; }
    if (/^\d+\.+$/.test(token) || /^\$\d+$/.test(token)) { i++; continue; }
    if (['1-0','0-1','1/2-1/2','*'].indexOf(token) !== -1) { i++; continue; }
    try {
      var mt = token.replace(/^\d+\.+/, '');
      var am = mt.match(/^(.+?)([!?]+)$/);
      var clean = am ? am[1] : mt, ann = am ? am[2] : '';
      var turn = branchChess.turn();
      var move = branchChess.move(clean, { sloppy: true });
      if (move) {
        var isBlack = (turn === 'b');
        var mn = lastNode.nodeId === 'root'
          ? (parseInt(lastNode.fen.split(' ')[5]) || 1)
          : (isBlack ? lastNode.moveNumber : lastNode.moveNumber + (lastNode.isBlackMove ? 1 : 0));
        var newNode = { san: move.san, annotation: ann, fen: branchChess.fen(), moveNumber: mn, isBlackMove: isBlack, comment: '', parent: lastNode, children: [], depth: depth, nodeId: 'pgn-node-' + (ctr.counter++) };
        lastNode.children.push(newNode);
        pgnNodeRegistry[newNode.nodeId] = newNode;
        lastNode = newNode;
      }
    } catch(e) {}
    i++;
  }
  return i;
}

// Move list rendering
function pgnRenderMoveTable(root) {
  var c = document.getElementById('pgnMoves'); c.innerHTML = '';
  if (root.children.length) pgnRenderSeq(root.children[0], c);
}
function pgnRenderSeq(start, container) {
  var node = start, lastNum = 0;
  while (node) {
    if (!node.isBlackMove && node.moveNumber !== lastNum) {
      var ns = document.createElement('span'); ns.className = 'move-number'; ns.textContent = node.moveNumber + '. '; container.appendChild(ns); lastNum = node.moveNumber;
    }
    var ms = document.createElement('span'); ms.className = 'move-san'; ms.textContent = node.san + (node.annotation||''); ms.dataset.nodeId = node.nodeId;
    ms.onclick = function() { pgnJumpToNode(this.dataset.nodeId); }; container.appendChild(ms);
    if (node.parent && node.parent.children.length > 1 && node.parent.children.indexOf(node) === 0) {
      for (var v = 1; v < node.parent.children.length; v++) pgnRenderVariation(node.parent.children[v], container);
    }
    node = node.children.length ? node.children[0] : null;
  }
}
function pgnRenderVariation(start, container) {
  var op = document.createElement('span'); op.className = 'variation-container'; op.textContent = '('; container.appendChild(op);
  var node = start, first = true;
  while (node) {
    if (first) { var ns = document.createElement('span'); ns.className = 'move-number'; ns.textContent = node.isBlackMove ? node.moveNumber+'... ' : node.moveNumber+'. '; container.appendChild(ns); first = false; }
    else if (!node.isBlackMove) { var ns2 = document.createElement('span'); ns2.className = 'move-number'; ns2.textContent = node.moveNumber+'. '; container.appendChild(ns2); }
    var ms = document.createElement('span'); ms.className = 'variation-move'; ms.textContent = node.san+(node.annotation||''); ms.dataset.nodeId = node.nodeId;
    ms.onclick = function() { pgnJumpToNode(this.dataset.nodeId); }; container.appendChild(ms); container.appendChild(document.createTextNode(' '));
    node = node.children.length ? node.children[0] : null;
  }
  var cp = document.createElement('span'); cp.className = 'variation-container'; cp.textContent = ') '; container.appendChild(cp);
}

// Navigation
function pgnJumpToNode(nodeId) {
  var node = pgnNodeRegistry[nodeId]; if (!node) return;
  pgnCurrent = node;
  if (pgnBoard) pgnBoard.position(node.fen);
  document.querySelectorAll('#pgnMoves .current').forEach(function(el) { el.classList.remove('current'); });
  var el = document.querySelector('#pgnMoves [data-node-id="' + nodeId + '"]');
  if (el) { el.classList.add('current'); el.scrollIntoView({ block: 'nearest' }); }
  document.getElementById('pgnComment').textContent = node.comment || '';
}
function pgnGoStart() { pgnJumpToNode('root'); }
function pgnGoEnd()   { var n = pgnCurrent||pgnRoot; while(n&&n.children.length) n=n.children[0]; if(n) pgnJumpToNode(n.nodeId); }
function pgnGoPrev()  { if(pgnCurrent&&pgnCurrent.parent) pgnJumpToNode(pgnCurrent.parent.nodeId); }
function pgnGoNext()  { if(pgnCurrent&&pgnCurrent.children.length) pgnJumpToNode(pgnCurrent.children[0].nodeId); }
function pgnFlip()    { if (pgnBoard) pgnBoard.flip(); }

document.addEventListener('keydown', function(e) {
  if (!document.getElementById('board-pane').classList.contains('visible')) return;
  if (e.key === 'ArrowRight') { e.preventDefault(); pgnGoNext(); }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); pgnGoPrev(); }
});

// ── Init ─────────────────────────────────────────────────────────────────────
buildNav();
if (REPORTS['comparison']) showReport('comparison');
else if (GAMES.length) showReport(GAMES[0].id);
</script>
</body>
</html>
"""


def generate_run_html(
    run_dir: Path,
    games: list[dict],
    stat_game_rows: list[dict] | None = None,
    stat_blunder_rows: list[dict] | None = None,
) -> None:
    """Generate report.html in the run folder with embedded PGNs, rendered reports, and stats tables."""

    # Read per-game and comparison .md files
    reports: dict = {}
    for g in games:
        md_path = run_dir / f"{g['id']}.md"
        if md_path.exists():
            reports[g["id"]] = md_path.read_text(encoding="utf-8")
    comp = run_dir / "comparison.md"
    if comp.exists():
        reports["comparison"] = comp.read_text(encoding="utf-8")

    # Copy PGNs into run folder and build embed data
    pgns: dict = {}
    for g in games:
        src = RAW_DIR / f"{g['id']}.pgn"
        if src.exists():
            pgn_text = src.read_text(encoding="utf-8")
            dest = run_dir / f"{g['id']}.pgn"
            dest.write_text(pgn_text, encoding="utf-8")
            pgns[g["id"]] = {
                "pgn":       pgn_text,
                "white":     g["white"],
                "black":     g["black"],
                "my_color":  g["my_color"],
                "my_result": g["my_result"],
                "url":       g.get("url", ""),
                "date":      g.get("date", ""),
            }

    games_list = [
        {
            "id":        g["id"],
            "white":     g["white"],
            "black":     g["black"],
            "my_color":  g["my_color"],
            "my_result": g["my_result"],
            "date":      g.get("date", ""),
            "url":       g.get("url", ""),
        }
        for g in games
    ]

    html = RUN_HTML_TEMPLATE
    html = html.replace("__GAMES_JSON__",   json.dumps(games_list,  separators=(",", ":")))
    html = html.replace("__PGNS_JSON__",    json.dumps(pgns,        separators=(",", ":")))
    html = html.replace("__REPORTS_JSON__", json.dumps(reports,     separators=(",", ":")))
    html = html.replace("__STATS_GAMES_JSON__",    json.dumps(stat_game_rows or [],    separators=(",", ":")))
    html = html.replace("__STATS_BLUNDERS_JSON__", json.dumps(stat_blunder_rows or [], separators=(",", ":")))

    out = run_dir / "report.html"
    out.write_text(html, encoding="utf-8")
    print(f"    → {out.name}")


if __name__ == "__main__":
    main()
