#!/usr/bin/env python3
"""
Generate tree_viewer.html — a self-contained interactive position-tree browser.

Reads <bucket>/tree.sqlite + <bucket>/raw/chesscom/*.pgn, embeds everything as
JSON, outputs <bucket>/tree_viewer.html — a file you can open directly in any
browser (no server required). Fully self-contained: safe to copy or send on
its own.

Usage (from chess-rag/, using a bucket key):
    python tree_viz.py tttstanley

Or from inside a bucket folder — no arguments needed:
    python tree_viz.py

Overrides:
    --db PATH  --pgn-dir PATH  --out PATH
"""

import argparse
import json
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent


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
        "Pass a bucket key (e.g. python tree_viz.py tttstanley) "
        "or run from inside a bucket folder (data/<key>/)."
    )

STARTING_KEY = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_tree(db_path: Path) -> dict:
    """
    Returns {position_key: {fen, children: [
        {san, uci, next, g, w, d, l, ids: [game_id, ...]}
    ]}}
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            e.position_key,
            p.fen,
            e.move_san,
            e.move_uci,
            e.next_position_key,
            COUNT(*)                                                        AS games,
            SUM(CASE
                    WHEN (e.my_color='white' AND e.result='1-0')
                      OR (e.my_color='black' AND e.result='0-1')
                    THEN 1 ELSE 0 END)                                      AS wins,
            SUM(CASE WHEN e.result='1/2-1/2' THEN 1 ELSE 0 END)            AS draws,
            SUM(CASE
                    WHEN (e.my_color='white' AND e.result='0-1')
                      OR (e.my_color='black' AND e.result='1-0')
                    THEN 1 ELSE 0 END)                                      AS losses,
            GROUP_CONCAT(e.game_id)                                         AS game_ids
        FROM edges e
        JOIN positions p ON p.position_key = e.position_key
        GROUP BY e.position_key, e.move_san, e.move_uci, e.next_position_key
        ORDER BY e.position_key, games DESC
        """
    ).fetchall()
    conn.close()

    tree: dict = {}
    for r in rows:
        pk = r["position_key"]
        if pk not in tree:
            tree[pk] = {"fen": r["fen"], "children": []}
        ids = list(dict.fromkeys((r["game_ids"] or "").split(",")))  # dedupe, preserve order
        tree[pk]["children"].append({
            "san": r["move_san"],
            "uci": r["move_uci"],
            "next": r["next_position_key"],
            "g": r["games"],
            "w": r["wins"],
            "d": r["draws"],
            "l": r["losses"],
            "ids": ids,
        })
    return tree


def _pgn_header(pgn: str, key: str) -> str:
    m = re.search(rf'\[{re.escape(key)}\s+"([^"]*)"\]', pgn)
    return m.group(1) if m else ""


def load_pgns(pgn_dir: Path) -> dict:
    """
    Returns {game_id: {pgn, white, black, result, date, my_color, my_result, url}}
    """
    pgns: dict = {}
    for path in pgn_dir.glob("*.pgn"):
        game_id = path.stem
        text = path.read_text(encoding="utf-8")
        pgns[game_id] = {
            "pgn": text,
            "white":     _pgn_header(text, "White"),
            "black":     _pgn_header(text, "Black"),
            "result":    _pgn_header(text, "Result"),
            "date":      _pgn_header(text, "Date") or _pgn_header(text, "EndDate"),
            "my_color":  _pgn_header(text, "MyColor"),
            "my_result": _pgn_header(text, "MyResult"),
            "url":       _pgn_header(text, "Link") or _pgn_header(text, "Site"),
        }
    return pgns


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>My Chess Opening Tree</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', system-ui, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 24px 16px 48px;
    min-height: 100vh;
  }
  h1 { color: #00d4ff; font-size: 1.3rem; margin-bottom: 16px; letter-spacing: 1px; }

  #breadcrumb {
    font-size: 0.85rem;
    color: #aaa;
    margin-bottom: 14px;
    min-height: 1.2em;
    word-break: break-word;
    max-width: 480px;
    text-align: center;
  }
  #breadcrumb span { color: #00d4ff; }

  /* ── Board ── */
  #board-wrap {
    width: 400px; height: 400px;
    border: 2px solid #333;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 6px;
  }
  #board {
    display: grid;
    grid-template-columns: repeat(8, 1fr);
    grid-template-rows: repeat(8, 1fr);
    width: 100%; height: 100%;
  }
  .sq {
    display: flex; align-items: center; justify-content: center;
    font-size: 2.8rem; line-height: 1;
    user-select: none;
  }
  .sq.light { background: #f5e8c8; }
  .sq.dark  { background: #c8956b; }
  .wp { color: #111; text-shadow: 0 0 2px #fff, 0 0 3px #fff, 0 0 1px #fff; }
  .bp { color: #fff; text-shadow: 0 0 2px #000, 0 0 3px #000, 0 0 1px #000; }
  .sq.hl    { outline: 3px inset #00d4ff; }

  #coords-files {
    display: flex; width: 400px;
    justify-content: space-around;
    font-size: 0.7rem; color: #666;
    margin-bottom: 16px; padding: 0 2px;
  }
  .file-label { width: 50px; text-align: center; }

  /* ── Controls ── */
  #controls { display: flex; gap: 10px; margin-bottom: 16px; }
  button {
    background: #0f3460; color: #00d4ff;
    border: 1px solid #00d4ff;
    padding: 6px 14px; border-radius: 5px;
    cursor: pointer; font-size: 0.85rem;
    transition: all 0.15s;
    white-space: nowrap;
  }
  button:hover { background: #00d4ff; color: #1a1a2e; }
  button:disabled { opacity: 0.4; cursor: not-allowed; }

  /* ── Moves table ── */
  .section { width: 480px; margin-bottom: 24px; }
  .section h2 { font-size: 0.9rem; color: #00d4ff; margin-bottom: 8px; }
  .none { color: #777; font-size: 0.85rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
  th {
    background: #0f3460; color: #00d4ff;
    padding: 6px 10px; text-align: left; font-weight: 600;
  }
  td { padding: 6px 10px; border-bottom: 1px solid #2a2a3e; }
  .move-row { cursor: pointer; transition: background 0.15s; }
  .move-row:hover td { background: #16213e; }
  .san { font-weight: 700; font-size: 1rem; color: #fff; }
  .bar-wrap {
    background: #2a2a3e; border-radius: 3px;
    height: 8px; overflow: hidden; min-width: 80px;
  }
  .bar-win  { display: inline-block; height: 8px; background: #28a745; }
  .bar-draw { display: inline-block; height: 8px; background: #888; }
  .bar-loss { display: inline-block; height: 8px; background: #dc3545; }
  .score { color: #00d4ff; font-weight: 600; }

  /* ── Games panel ── */
  #games-section { width: 480px; }
  #games-section h2 { font-size: 0.9rem; color: #00d4ff; margin-bottom: 8px; }
  #games-toolbar {
    display: flex; gap: 8px; align-items: center;
    margin-bottom: 10px; flex-wrap: wrap;
  }
  #games-toolbar label { font-size: 0.82rem; color: #aaa; cursor: pointer; }
  .game-row {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 10px; border-bottom: 1px solid #2a2a3e;
    font-size: 0.85rem;
  }
  .game-row input[type=checkbox] { cursor: pointer; accent-color: #00d4ff; }
  .game-info { flex: 1; }
  .game-info .players { font-weight: 600; color: #fff; }
  .game-info .meta { color: #999; font-size: 0.78rem; margin-top: 2px; }
  .result-win  { color: #28a745; font-weight: 700; }
  .result-loss { color: #dc3545; font-weight: 700; }
  .result-draw { color: #aaa;    font-weight: 700; }
  .btn-copy-one {
    background: #0f3460; color: #00d4ff;
    border: 1px solid #00d4ff;
    padding: 4px 10px; border-radius: 4px;
    cursor: pointer; font-size: 0.78rem;
    white-space: nowrap; transition: all 0.15s;
  }
  .btn-copy-one:hover { background: #00d4ff; color: #1a1a2e; }
  .btn-copy-one.copied { background: #28a745; border-color: #28a745; color: #fff; }

  /* PGN panel (fixed right, no veil) */
  #pgnPanel { display: none; position: fixed; top: 0; right: 0; width: 420px; height: 100vh; background: #12122a; border-left: 1px solid #2a2a4e; flex-direction: column; z-index: 100; box-shadow: -4px 0 16px rgba(0,0,0,0.4); }
  #pgnPanel.open { display: flex; }
  #pgn-header { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid #2a2a4e; flex-shrink: 0; }
  #pgn-caption { font-size: 0.78rem; color: #aaa; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pgn-close { background: none; border: none; color: #666; font-size: 1.2rem; cursor: pointer; padding: 0 4px; line-height: 1; flex-shrink: 0; }
  .pgn-close:hover { color: #ccc; }
  #pgn-body { display: flex; flex-direction: column; align-items: center; padding: 12px; flex: 1; overflow: hidden; }
  #pgnModalBoard { width: 380px; height: 380px; flex-shrink: 0; }
  .pgn-controls { margin-top: 8px; display: flex; gap: 8px; justify-content: center; flex-shrink: 0; }
  .pgn-controls button { padding: 4px 12px; border-radius: 4px; border: 1px solid #444; background: #2a2a3a; color: #ccc; cursor: pointer; font-size: 1rem; }
  .pgn-controls button:hover { background: #3a3a4a; }
  .pgn-comment { margin-top: 6px; width: 100%; min-height: 1.1em; font-size: 12px; font-style: italic; color: #ffd700; text-align: center; flex-shrink: 0; }
  .pgn-moves { margin-top: 8px; width: 100%; flex: 1; overflow-y: auto; background: #1e1e30; color: #ddd; padding: 10px 12px; border-radius: 4px; font-size: 13px; line-height: 2; user-select: none; }
  .pgn-moves .move-number { color: #666; }
  .pgn-moves .move-san { cursor: pointer; padding: 2px 4px; border-radius: 3px; font-weight: 600; }
  .pgn-moves .move-san:hover { background: #2a3a4a; }
  .pgn-moves .move-san.current { background: #7a5d10; color: #fff; }
  .pgn-moves .variation-container { color: #666; }
  .pgn-moves .variation-move { cursor: pointer; padding: 1px 3px; border-radius: 3px; font-weight: 500; color: #aaa; }
  .pgn-moves .variation-move:hover { background: #2a3a4a; }
  .pgn-moves .variation-move.current { background: #7a5d10; color: #fff; }
</style>
</head>
<body>
<h1>My Chess Opening Tree</h1>
<div id="breadcrumb">Starting position</div>

<div id="controls">
  <button id="btn-back" disabled onclick="goBack()">← Back</button>
  <button onclick="goHome()">⌂ Root</button>
  <button onclick="flipBoard()">⇅ Flip</button>
</div>

<div id="board-wrap"><div id="board"></div></div>
<div id="coords-files">
  <span class="file-label">a</span><span class="file-label">b</span>
  <span class="file-label">c</span><span class="file-label">d</span>
  <span class="file-label">e</span><span class="file-label">f</span>
  <span class="file-label">g</span><span class="file-label">h</span>
</div>

<div class="section">
  <h2>Moves from this position <span id="position-arg" style="font-size:0.75rem;color:#666;font-weight:400"></span></h2>
  <div id="moves-content"></div>
</div>

<div id="games-section">
  <h2 id="games-heading">Games at this position</h2>
  <div id="games-toolbar" style="display:none">
    <label><input type="checkbox" id="chk-all" onchange="toggleAll(this)"> Select all</label>
    <button onclick="copySelected()">Copy selected PGN(s)</button>
    <button onclick="copyAll()">Copy all PGN(s)</button>
  </div>
  <div id="games-list"></div>
</div>

<div id="pgnPanel">
  <div id="pgn-header">
    <span id="pgn-caption"></span>
    <button class="pgn-close" onclick="closePgnModal()" title="Close">✕</button>
  </div>
  <div id="pgn-body">
    <div id="pgnModalBoard"></div>
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
const TREE = __TREE_JSON__;
const PGNS = __PGNS_JSON__;
const STARTING_KEY = __STARTING_KEY__;

const PIECES = {
  K:'♔',Q:'♕',R:'♖',B:'♗',N:'♘',P:'♙',
  k:'♚',q:'♛',r:'♜',b:'♝',n:'♞',p:'♟',
};

// ── State ─────────────────────────────────────────────────────────────────
let history = [];        // [{key, san}]
let currentKey = STARTING_KEY;
let lastUci = null;
let flipped = false;

// ── Board ─────────────────────────────────────────────────────────────────
function fenToGrid(fen) {
  return fen.split(' ')[0].split('/').map(rank => {
    const row = [];
    for (const ch of rank) {
      if (/\d/.test(ch)) for (let i = 0; i < +ch; i++) row.push('');
      else row.push(ch);
    }
    return row;
  });
}

function renderBoard(fen, uci) {
  const grid = fenToGrid(fen);
  const board = document.getElementById('board');
  board.innerHTML = '';
  const hlFrom = uci ? uci.slice(0,2) : null;
  const hlTo   = uci ? uci.slice(2,4) : null;
  for (let r = 0; r < 8; r++) {
    for (let f = 0; f < 8; f++) {
      const rr = flipped ? 7 - r : r;
      const ff = flipped ? 7 - f : f;
      const sq = document.createElement('div');
      const sqName = String.fromCharCode(97+ff) + (8-rr);
      sq.className = 'sq ' + ((rr+ff)%2===0 ? 'light' : 'dark');
      if (sqName===hlFrom || sqName===hlTo) sq.classList.add('hl');
      const p = grid[rr][ff];
      if (p) sq.innerHTML = `<span class="${p === p.toUpperCase() ? 'wp' : 'bp'}">${PIECES[p] || ''}</span>`;
      board.appendChild(sq);
    }
  }
  // File labels follow orientation
  document.querySelectorAll('#coords-files .file-label').forEach((el, i) => {
    el.textContent = String.fromCharCode(97 + (flipped ? 7 - i : i));
  });
}

function flipBoard() {
  flipped = !flipped;
  update();
}

// ── Moves table ───────────────────────────────────────────────────────────
function renderMoves(key) {
  const node = TREE[key];
  const el = document.getElementById('moves-content');
  if (!node || !node.children.length) {
    el.innerHTML = '<p class="none">No recorded games from this position.</p>';
    return;
  }
  let html = `<table><thead><tr>
    <th>Move</th><th>Games</th><th>W / D / L</th><th>Score</th><th>Bar</th>
  </tr></thead><tbody>`;
  for (const c of node.children) {
    const pct  = c.g > 0 ? Math.round(100*c.w/c.g) : 0;
    const wPct = c.g > 0 ? (100*c.w/c.g).toFixed(1) : 0;
    const dPct = c.g > 0 ? (100*c.d/c.g).toFixed(1) : 0;
    const lPct = c.g > 0 ? (100*c.l/c.g).toFixed(1) : 0;
    html += `<tr class="move-row" onclick="navigate('${c.next}','${c.san}','${c.uci}')">
      <td class="san">${c.san}</td>
      <td>${c.g}</td>
      <td>+${c.w} =${c.d} -${c.l}</td>
      <td class="score">${pct}%</td>
      <td><div class="bar-wrap">
        <span class="bar-win"  style="width:${wPct}%"></span><span
              class="bar-draw" style="width:${dPct}%"></span><span
              class="bar-loss" style="width:${lPct}%"></span>
      </div></td>
    </tr>`;
  }
  html += '</tbody></table>';
  el.innerHTML = html;
}

// ── Games panel ───────────────────────────────────────────────────────────
function gamesAtPosition(key) {
  const node = TREE[key];
  if (!node) return [];
  // Union of all game_ids across all children (games that were AT this position)
  const seen = new Set();
  const ids = [];
  for (const c of node.children) {
    for (const id of (c.ids || [])) {
      if (!seen.has(id)) { seen.add(id); ids.push(id); }
    }
  }
  return ids;
}

function resultClass(myResult) {
  if (myResult === 'win')  return 'result-win';
  if (myResult === 'loss') return 'result-loss';
  return 'result-draw';
}
function resultLabel(myResult) {
  if (myResult === 'win')  return 'Win';
  if (myResult === 'loss') return 'Loss';
  return 'Draw';
}

function renderGames(key) {
  const ids = gamesAtPosition(key);
  const heading = document.getElementById('games-heading');
  const toolbar = document.getElementById('games-toolbar');
  const list    = document.getElementById('games-list');

  heading.textContent = `Games at this position (${ids.length})`;

  if (!ids.length) {
    toolbar.style.display = 'none';
    list.innerHTML = '<p class="none" style="margin-top:6px">No games reached this position.</p>';
    return;
  }

  toolbar.style.display = 'flex';
  document.getElementById('chk-all').checked = false;

  let html = '';
  for (let i = 0; i < ids.length; i++) {
    const id = ids[i];
    const g  = PGNS[id];
    if (!g) continue;
    const rc = resultClass(g.my_result);
    const rl = resultLabel(g.my_result);
    const asColor = g.my_color ? ` as ${g.my_color}` : '';
    html += `<div class="game-row">
      <input type="checkbox" class="game-chk" data-id="${id}">
      <div class="game-info">
        <div class="players">${g.white} vs ${g.black}</div>
        <div class="meta">
          <span class="${rc}">${rl}</span>${asColor}
          &nbsp;·&nbsp;${g.date || '?'}
          ${g.url ? `&nbsp;·&nbsp;<a href="${g.url}" target="_blank" style="color:#00d4ff">chess.com</a>` : ''}
        </div>
      </div>
      <button class="btn-copy-one" onclick="openPgnModal('${id}')">View</button>
      <button class="btn-copy-one" onclick="copyId('${id}', this)">Copy ID</button>
      <button class="btn-copy-one" onclick="copyOne('${id}', this)">Copy PGN</button>
    </div>`;
  }
  list.innerHTML = html;
}

// ── Copy helpers ──────────────────────────────────────────────────────────
async function copyId(id, btn) {
  try {
    const current = await navigator.clipboard.readText().catch(() => '');
    const sep = current.trim() ? ' ' : '';
    await navigator.clipboard.writeText(current.trim() + sep + id);
    btn.textContent = 'Appended!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy ID'; btn.classList.remove('copied'); }, 1500);
  } catch (err) {
    navigator.clipboard.writeText(id);
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy ID'; btn.classList.remove('copied'); }, 1500);
  }
}

async function copyOne(id, btn) {
  const g = PGNS[id];
  if (!g) return;
  try {
    const current = await navigator.clipboard.readText().catch(() => '');
    const sep = current.trim() ? '\n\n' : '';
    await navigator.clipboard.writeText(current.trim() + sep + g.pgn.trim());
    btn.textContent = 'Appended!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy PGN'; btn.classList.remove('copied'); }, 1500);
  } catch (err) {
    // fallback: just overwrite
    navigator.clipboard.writeText(g.pgn.trim());
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy PGN'; btn.classList.remove('copied'); }, 1500);
  }
}

function selectedIds() {
  return [...document.querySelectorAll('.game-chk:checked')].map(el => el.dataset.id);
}

function copySelected() {
  const ids = selectedIds();
  if (!ids.length) { alert('Select at least one game first.'); return; }
  const text = ids.map(id => PGNS[id]?.pgn?.trim()).filter(Boolean).join('\n\n');
  navigator.clipboard.writeText(text).then(() => alert(`Copied ${ids.length} PGN(s) to clipboard.`));
}

function copyAll() {
  const ids = gamesAtPosition(currentKey);
  const text = ids.map(id => PGNS[id]?.pgn?.trim()).filter(Boolean).join('\n\n');
  navigator.clipboard.writeText(text).then(() => alert(`Copied ${ids.length} PGN(s) to clipboard.`));
}

function toggleAll(chk) {
  document.querySelectorAll('.game-chk').forEach(el => el.checked = chk.checked);
}

// ── Navigation ────────────────────────────────────────────────────────────
function navigate(nextKey, san, uci) {
  history.push({ key: currentKey, san });
  currentKey = nextKey;
  lastUci = uci;
  update();
}

function goBack() {
  if (!history.length) return;
  const prev = history.pop();
  currentKey = prev.key;
  lastUci = null;
  update();
}

function goHome() {
  history = [];
  currentKey = STARTING_KEY;
  lastUci = null;
  update();
}

function update() {
  const node = TREE[currentKey];
  const fen  = node ? node.fen : currentKey + ' 0 1';
  renderBoard(fen, lastUci);

  const moves = history.map(h => h.san).join(' ');
  document.getElementById('breadcrumb').innerHTML =
    moves ? `<span>${moves}</span>` : 'Starting position';
  document.getElementById('position-arg').textContent =
    moves ? `--position "${moves}"` : '';

  renderMoves(currentKey);
  renderGames(currentKey);
  document.getElementById('btn-back').disabled = history.length === 0;
}

update();

// ── PGN modal ─────────────────────────────────────────────────────────────
var pgnModalBoard = null, pgnRoot = null, pgnCurrent = null, pgnNodeRegistry = {};
var pgnLibsState = 'none', pgnLibsCallbacks = [];

function ensureChessLibs(cb) {
  if (pgnLibsState === 'ready') { cb(); return; }
  pgnLibsCallbacks.push(cb);
  if (pgnLibsState === 'loading') return;
  pgnLibsState = 'loading';
  function loadScript(src, next) {
    const s = document.createElement('script'); s.src = src; s.onload = next;
    s.onerror = () => { document.getElementById('pgnMoves').textContent = 'Failed to load chess libs (internet required).'; };
    document.head.appendChild(s);
  }
  const link = document.createElement('link'); link.rel = 'stylesheet';
  link.href = 'https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.css';
  document.head.appendChild(link);
  loadScript('https://cdnjs.cloudflare.com/ajax/libs/jquery/2.2.4/jquery.min.js', () =>
    loadScript('https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.js', () =>
      loadScript('https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js', () => {
        pgnLibsState = 'ready';
        const cbs = pgnLibsCallbacks; pgnLibsCallbacks = [];
        cbs.forEach(f => f());
      })
    )
  );
}

function openPgnModal(id) {
  const g = PGNS[id]; if (!g) return;
  document.getElementById('pgn-caption').textContent = `${g.white} vs ${g.black}  ·  ${g.date || ''}  ·  ${g.my_result || ''} as ${g.my_color || ''}`;
  document.getElementById('pgnMoves').innerHTML = 'Loading\u2026';
  document.getElementById('pgnComment').textContent = '';
  document.getElementById('pgnPanel').classList.add('open');
  ensureChessLibs(() => renderPgnText(g.pgn));
}

function closePgnModal() {
  document.getElementById('pgnPanel').classList.remove('open');
}

function renderPgnText(text) {
  const hits = []; let m; const re = /^\[Event /gm;
  while ((m = re.exec(text)) !== null) hits.push(m.index);
  if (hits.length > 1) text = text.slice(0, hits[1]);
  pgnRoot = pgnParse(text);
  if (!pgnModalBoard) {
    pgnModalBoard = Chessboard('pgnModalBoard', { draggable: false, position: pgnRoot.fen, pieceTheme: 'https://assets.codepen.io/1075762/{piece}.png' });
  } else { pgnModalBoard.position(pgnRoot.fen); }
  pgnRenderMoves(pgnRoot);
  pgnJump('root');
}

function pgnTokenize(mt) {
  const tokens = []; let cur = '', inC = false;
  for (const ch of mt) {
    if (ch === '{') { if (cur.trim()) tokens.push(cur.trim()); cur = '{'; inC = true; }
    else if (ch === '}') { cur += '}'; tokens.push(cur); cur = ''; inC = false; }
    else if (inC) { cur += ch; }
    else if (ch === '(' || ch === ')') { if (cur.trim()) tokens.push(cur.trim()); tokens.push(ch); cur = ''; }
    else if (/\s/.test(ch)) { if (cur.trim()) tokens.push(cur.trim()); cur = ''; }
    else { cur += ch; }
  }
  if (cur.trim()) tokens.push(cur.trim());
  return tokens;
}

function pgnParse(pgnString) {
  const fm = pgnString.match(/\[FEN\s+"([^"]+)"\]/);
  const startFen = fm ? fm[1] : 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  const chess = new Chess(); try { chess.load(startFen); } catch(e) { chess.reset(); }
  const root = { san: null, fen: chess.fen(), moveNumber: 0, isBlackMove: false, comment: '', annotation: '', parent: null, children: [], nodeId: 'root' };
  pgnNodeRegistry = { root };
  pgnParseTokens(pgnTokenize(pgnString.replace(/\[.*?\]/g, '').trim()), 0, chess, root, { n: 0 });
  return root;
}

function pgnParseTokens(tokens, i, chess, parent, ctr) {
  let last = parent;
  while (i < tokens.length) {
    const t = tokens[i];
    if (t === '(') {
      const bp = last.parent || parent;
      const vc = new Chess(); vc.load(bp.fen);
      i = pgnParseTokens(tokens, i + 1, vc, bp, ctr); continue;
    }
    if (t === ')') return i + 1;
    if (t[0] === '{') { if (last !== parent) last.comment = t.slice(1,-1).trim(); i++; continue; }
    if (/^\d+\.+$/.test(t) || /^\$\d+$/.test(t)) { i++; continue; }
    if (['1-0','0-1','1/2-1/2','*'].includes(t)) { i++; continue; }
    try {
      const clean = t.replace(/^\d+\.+/,'').replace(/[!?]+$/,'');
      const ann   = (t.match(/[!?]+$/) || [''])[0];
      const turn  = chess.turn();
      const move  = chess.move(clean, { sloppy: true });
      if (move) {
        const isBlack = turn === 'b';
        const mn = last.nodeId === 'root'
          ? (parseInt(last.fen.split(' ')[5]) || 1)
          : (isBlack ? last.moveNumber : last.moveNumber + (last.isBlackMove ? 1 : 0));
        const node = { san: move.san, annotation: ann, fen: chess.fen(), moveNumber: mn, isBlackMove: isBlack, comment: '', parent: last, children: [], nodeId: 'n' + (ctr.n++) };
        last.children.push(node); pgnNodeRegistry[node.nodeId] = node; last = node;
      }
    } catch(e) {}
    i++;
  }
  return i;
}

function pgnRenderMoves(root) {
  const c = document.getElementById('pgnMoves'); c.innerHTML = '';
  if (root.children.length) pgnRenderSeq(root.children[0], c);
}
function pgnRenderSeq(start, c) {
  let node = start, lastNum = 0;
  while (node) {
    if (!node.isBlackMove && node.moveNumber !== lastNum) {
      const ns = document.createElement('span'); ns.className = 'move-number'; ns.textContent = node.moveNumber + '. '; c.appendChild(ns); lastNum = node.moveNumber;
    }
    const ms = document.createElement('span'); ms.className = 'move-san'; ms.textContent = node.san + (node.annotation||''); ms.dataset.nodeId = node.nodeId;
    ms.onclick = function() { pgnJump(this.dataset.nodeId); }; c.appendChild(ms);
    if (node.parent && node.parent.children.length > 1 && node.parent.children[0] === node)
      for (let v = 1; v < node.parent.children.length; v++) pgnRenderVar(node.parent.children[v], c);
    node = node.children[0] || null;
  }
}
function pgnRenderVar(start, c) {
  const op = document.createElement('span'); op.className = 'variation-container'; op.textContent = '('; c.appendChild(op);
  let node = start, first = true;
  while (node) {
    if (first) { const ns = document.createElement('span'); ns.className = 'move-number'; ns.textContent = node.isBlackMove ? node.moveNumber+'... ' : node.moveNumber+'. '; c.appendChild(ns); first = false; }
    else if (!node.isBlackMove) { const ns = document.createElement('span'); ns.className = 'move-number'; ns.textContent = node.moveNumber+'. '; c.appendChild(ns); }
    const ms = document.createElement('span'); ms.className = 'variation-move'; ms.textContent = node.san+(node.annotation||''); ms.dataset.nodeId = node.nodeId;
    ms.onclick = function() { pgnJump(this.dataset.nodeId); }; c.appendChild(ms); c.appendChild(document.createTextNode(' '));
    node = node.children[0] || null;
  }
  const cp = document.createElement('span'); cp.className = 'variation-container'; cp.textContent = ') '; c.appendChild(cp);
}

function pgnJump(nodeId) {
  const node = pgnNodeRegistry[nodeId]; if (!node) return;
  pgnCurrent = node;
  if (pgnModalBoard) pgnModalBoard.position(node.fen);
  document.querySelectorAll('#pgnMoves .current').forEach(el => el.classList.remove('current'));
  const el = document.querySelector(`#pgnMoves [data-node-id="${nodeId}"]`);
  if (el) { el.classList.add('current'); el.scrollIntoView({ block: 'nearest' }); }
  document.getElementById('pgnComment').textContent = node.comment || '';
}
function pgnGoStart() { pgnJump('root'); }
function pgnGoEnd()   { let n = pgnCurrent||pgnRoot; while(n&&n.children.length) n=n.children[0]; if(n) pgnJump(n.nodeId); }
function pgnGoPrev()  { if(pgnCurrent?.parent) pgnJump(pgnCurrent.parent.nodeId); }
function pgnGoNext()  { if(pgnCurrent?.children.length) pgnJump(pgnCurrent.children[0].nodeId); }
function pgnFlip()    { if (pgnModalBoard) pgnModalBoard.flip(); }

document.addEventListener('keydown', e => {
  if (!document.getElementById('pgnPanel').classList.contains('open')) return;
  if (e.key === 'ArrowRight') { e.preventDefault(); pgnGoNext(); }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); pgnGoPrev(); }
  else if (e.key === 'Escape') closePgnModal();
});
</script>
</body>
</html>
"""


def generate(db_path: Path, pgn_dir: Path, out_path: Path, title: str) -> None:
    print(f"Loading tree from {db_path}…")
    tree = load_tree(db_path)
    print(f"  {len(tree)} positions with moves")

    print(f"Loading PGNs from {pgn_dir}…")
    pgns = load_pgns(pgn_dir)
    print(f"  {len(pgns)} games")

    tree_json    = json.dumps(tree, separators=(",", ":"))
    pgns_json    = json.dumps(pgns, separators=(",", ":"))
    starting_json = json.dumps(STARTING_KEY)

    html = HTML_TEMPLATE.replace("__TREE_JSON__", tree_json)
    html = html.replace("__PGNS_JSON__", pgns_json)
    html = html.replace("__STARTING_KEY__", starting_json)
    html = html.replace("My Chess Opening Tree", title)  # <title> and <h1>

    out_path.write_text(html, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"  Written → {out_path}  ({size_kb} KB)")
    print(f"  Open:  open {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate interactive position-tree viewer")
    parser.add_argument(
        "key", nargs="?",
        help="Bucket key (data/<key>/); not needed when running inside a bucket folder",
    )
    parser.add_argument("--db",  default=None, help="default: <bucket>/tree.sqlite")
    parser.add_argument("--pgn-dir", default=None, help="default: <bucket>/raw/chesscom")
    parser.add_argument("--out", default=None, help="default: <bucket>/tree_viewer.html")
    args = parser.parse_args()

    bucket   = resolve_bucket(args.key)
    db_path  = Path(args.db) if args.db else bucket / "tree.sqlite"
    pgn_dir  = Path(args.pgn_dir) if args.pgn_dir else bucket / "raw" / "chesscom"
    out_path = Path(args.out) if args.out else bucket / "tree_viewer.html"

    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}\nRun tree_engine.py first.")

    generate(db_path, pgn_dir, out_path, title=f"{bucket.name} — Chess Opening Tree")


if __name__ == "__main__":
    main()
