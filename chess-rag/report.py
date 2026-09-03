#!/usr/bin/env python3
"""
Prototype: AI game report for a group of games from the same opening position.

Usage:
    python report.py <game_id> [game_id ...]
    python report.py 164380092682 171996841806 172074667356

    # Or pass the position moves to auto-find all games that went through it:
    python report.py --position "d4 d5 e3 Nc6 Bd3 Nf6 f4"

Output:
    reports/<timestamp>_<position>/
        run_meta.json      — position, games, timestamp
        <game_id>.md       — per-game report
        comparison.md      — cross-game comparison (wins vs losses)

Requires:
    pip install openai python-chess
    export OPENAI_API_KEY=sk-...
"""

import argparse
import json
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
RAW_DIR = HERE / "data" / "raw" / "chesscom"
DB_PATH = HERE / "data" / "tree.sqlite"
REPORTS_DIR = HERE / "reports"
KNOWLEDGE_PATH = HERE.parent / "chess_knowledge.txt"  # root-level file

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_knowledge() -> str:
    """Load chess_knowledge.txt as plain context string."""
    if KNOWLEDGE_PATH.exists():
        return KNOWLEDGE_PATH.read_text(encoding="utf-8")
    # Fallback: look in the same directory
    alt = HERE / "chess_knowledge.txt"
    if alt.exists():
        return alt.read_text(encoding="utf-8")
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
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AI game reports")
    parser.add_argument("game_ids", nargs="*", help="Game IDs to analyze")
    parser.add_argument(
        "--position", "-p", metavar="MOVES",
        help='SAN moves to auto-find all games (e.g. "d4 d5 e3 Nc6 Bd3 Nf6 f4")',
    )
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model (default: gpt-4o)")
    args = parser.parse_args()

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
    print(f"Analyzing {len(games)} game(s) with {args.model}...\n")

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
            f"{report}\n",
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
    generate_run_html(run_dir, games)

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
    </div>
    <div class="pgn-comment" id="pgnComment"></div>
    <div class="pgn-moves" id="pgnMoves"></div>
  </div>
</div>

<script>
const GAMES   = __GAMES_JSON__;
const PGNS    = __PGNS_JSON__;
const REPORTS = __REPORTS_JSON__;

// ── Sidebar nav ──────────────────────────────────────────────────────────────
var currentGameId = null;

function buildNav() {
  var nav = document.getElementById('nav-list');
  var html = '';
  if (REPORTS['comparison']) {
    html += '<div class="nav-item" data-id="comparison" onclick="showReport(\'comparison\')">📊 Comparison</div>';
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
  document.getElementById('md-output').innerHTML = simpleMarkdown(REPORTS[id] || '_(no report)_');
  document.getElementById('content-area').scrollTop = 0;
  var playBtn = document.getElementById('play-btn');
  var title   = document.getElementById('toolbar-title');
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

// ── Markdown renderer ────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function simpleMarkdown(md) {
  var lines = md.split('\n'), out = [], inList = false;
  lines.forEach(function(l) {
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


def generate_run_html(run_dir: Path, games: list[dict]) -> None:
    """Generate report.html in the run folder with embedded PGNs and rendered reports."""

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

    out = run_dir / "report.html"
    out.write_text(html, encoding="utf-8")
    print(f"    → {out.name}")


if __name__ == "__main__":
    main()
