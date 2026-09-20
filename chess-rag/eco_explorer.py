#!/usr/bin/env python3
"""
Generate eco_explorer.html — a standalone reference browser for the full ECO
opening classification (A-E), independent of any played games.

Unlike tree_viewer.html (which only shows openings encountered in recorded
games), this page always shows the complete classification: browse by
volume -> code -> named line, search by name across everything, or sort the
whole list by move sequence. Selecting a line opens a board + move-list
detail view with step-through, styled to match tree_viewer.html's existing
opening-detail modal.

Usage:
    python eco_explorer.py [--eco-cache ./eco_openings.json] [--out ./eco_explorer.html] [--refresh-cache]
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import requests as _requests
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False

HERE = Path(__file__).resolve().parent
DEFAULT_CACHE = HERE / "eco_openings.json"
DEFAULT_OUT = HERE / "eco_explorer.html"

ECO_BASE_URL = "https://raw.githubusercontent.com/hayatbiralem/eco.json/master/eco{}.json"
ECO_LETTERS = list("ABCDE")

_MOVE_NUM_RE = re.compile(r"^\d+\.+$")
_RESULT_TOKENS = {"1-0", "0-1", "1/2-1/2", "*"}


def _fen_to_key(fen: str) -> str:
    """Strip halfmove + fullmove counters from a full FEN -> 4-field position key."""
    return " ".join(fen.split()[:4])


def _parse_moves(moves_str: str) -> list:
    """'1. e4 e5 2. Nf3' -> ['e4', 'e5', 'Nf3']"""
    if not moves_str:
        return []
    out = []
    for tok in moves_str.split():
        if _MOVE_NUM_RE.match(tok) or tok in _RESULT_TOKENS:
            continue
        out.append(tok)
    return out


def fetch_upstream_moves() -> dict:
    """Fetch eco{A-E}.json from GitHub, return {4-field-fen-key: [SAN, ...]}."""
    if not HAVE_REQUESTS:
        print("  [warn] requests not installed - cannot fetch move sequences (pip install requests)")
        return {}
    moves_by_key = {}
    for letter in ECO_LETTERS:
        url = ECO_BASE_URL.format(letter)
        try:
            resp = _requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            for fen, entry in data.items():
                key = _fen_to_key(fen)
                moves_by_key[key] = _parse_moves(entry.get("moves", ""))
            print(f"    eco{letter}.json - {len(data)} entries")
        except Exception as e:
            print(f"  [warn] Could not fetch eco{letter}.json: {e}")
    return moves_by_key


def augment_eco_cache(cache_path: Path, force_refresh: bool = False) -> dict:
    """
    Ensure every entry in eco_openings.json carries a 'moves' field (SAN array).
    Existing 'eco'/'name' values are never modified. Writes the cache back to
    cache_path only when it needed updating.
    """
    if not cache_path.exists():
        print(f"  [error] ECO cache not found at {cache_path}")
        print("  Run tree_viz.py once first to build it, or pass --eco-cache.")
        sys.exit(1)

    cache = json.loads(cache_path.read_text())
    needs_moves = force_refresh or any("moves" not in entry for entry in cache.values())

    if not needs_moves:
        print(f"  ECO cache already has move sequences -> {cache_path}")
        return cache

    print("  Fetching move sequences from upstream ECO source...")
    moves_by_key = fetch_upstream_moves()

    if not moves_by_key:
        print("  [warn] No upstream data fetched - leaving entries without moves as data gaps")
        for entry in cache.values():
            entry.setdefault("moves", [])
        return cache

    filled = 0
    for key, entry in cache.items():
        if force_refresh or "moves" not in entry:
            entry["moves"] = moves_by_key.get(key, [])
            if entry["moves"]:
                filled += 1

    cache_path.write_text(json.dumps(cache, separators=(",", ":")))
    print(f"  ECO cache updated with move sequences -> {cache_path}  ({filled}/{len(cache)} lines have moves)")
    return cache


def build_line_records(cache: dict) -> list:
    """FEN-keyed cache dict -> [{'eco','name','moves','fen'}, ...], grouped by code."""
    records = []
    for fen, entry in cache.items():
        records.append({
            "eco": entry.get("eco", ""),
            "name": entry.get("name", ""),
            "moves": entry.get("moves") or [],
            "fen": fen,
        })
    records.sort(key=lambda r: (r["eco"], r["name"]))
    return records


def write_page(records: list, out_path: Path) -> None:
    lines_json = json.dumps(records, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("__ECO_LINES_JSON__", lines_json)
    out_path.write_text(html, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"  Written -> {out_path}  ({size_kb} KB, {len(records)} lines)")
    print(f"  Open:  open {out_path}")


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ECO Opening Explorer</title>
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
  h1 { color: #00d4ff; font-size: 1.3rem; margin-bottom: 4px; letter-spacing: 1px; }
  #subtitle { font-size: 0.78rem; color: #888; margin-bottom: 18px; text-align: center; max-width: 480px; }

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

  /* ── Top bar: volume tabs + search + sort ── */
  #top-bar { width: 640px; max-width: 100%; margin-bottom: 10px; }
  #volume-tabs { display: flex; gap: 4px; margin-bottom: 10px; flex-wrap: wrap; }
  .vol-tab {
    background: #0f3460; color: #aaa;
    border: 1px solid #2a4080;
    padding: 5px 18px; border-radius: 5px;
    cursor: pointer; font-size: 0.88rem; transition: all 0.15s;
  }
  .vol-tab:hover { border-color: #00d4ff; color: #00d4ff; }
  .vol-tab.active { background: #00d4ff; color: #1a1a2e; border-color: #00d4ff; font-weight: 700; }

  #controls-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
  #search-input {
    background: #0f3460; color: #ccc; border: 1px solid #2a4080;
    padding: 6px 12px; border-radius: 12px; font-size: 0.85rem; width: 240px;
  }
  #search-input:focus { outline: none; border-color: #00d4ff; }
  #search-input::placeholder { color: #555; }
  #sort-select {
    background: #0f3460; color: #ccc; border: 1px solid #2a4080;
    padding: 6px 10px; border-radius: 5px; font-size: 0.82rem;
  }
  #sort-label { font-size: 0.8rem; color: #aaa; }

  #breadcrumb { font-size: 0.8rem; color: #888; margin-bottom: 6px; min-height: 1.2em; }
  #breadcrumb span.crumb { color: #00d4ff; cursor: pointer; }
  #breadcrumb span.crumb:hover { text-decoration: underline; }
  #list-summary { font-size: 0.75rem; color: #888; margin-bottom: 8px; min-height: 1em; }

  /* ── List panel ── */
  #list-panel {
    width: 640px; max-width: 100%;
    max-height: 480px; overflow-y: auto;
    border: 1px solid #2a2a4e; border-radius: 6px;
    background: #14142c;
  }
  table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
  th {
    background: #0f3460; color: #00d4ff;
    padding: 6px 10px; text-align: left; font-weight: 600;
    position: sticky; top: 0;
  }
  td { padding: 6px 10px; border-bottom: 1px solid #2a2a3e; }
  .row-clickable { cursor: pointer; transition: background 0.12s; }
  .row-clickable:hover td { background: #16213e; }
  .row-clickable.seq-break td { border-top: 2px solid #00d4ff; }
  .none { color: #777; font-size: 0.85rem; padding: 14px; }
  .eco-badge {
    display: inline-block; background: #0f3460; color: #00d4ff;
    border: 1px solid #1a4a90; border-radius: 3px;
    padding: 0 5px; font-size: 0.72rem; font-weight: 700;
    font-family: monospace; white-space: nowrap;
  }
  .op-name { color: #e0e0e0; }
  .move-preview { color: #999; font-size: 0.78rem; font-family: monospace; }
  .gap-marker { color: #dc3545; font-size: 0.72rem; margin-left: 6px; }
  .count-cell { color: #aaa; text-align: right; }

  /* ── Line detail modal ── */
  #detail-veil {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.65); z-index: 200;
    align-items: flex-start; justify-content: center;
    padding-top: 60px;
  }
  #detail-veil.open { display: flex; }
  #detail-modal {
    background: #12122a; border: 1px solid #2a2a4e;
    border-radius: 8px; width: 560px; max-width: 92vw; max-height: 82vh;
    display: flex; flex-direction: column;
    box-shadow: 0 8px 40px rgba(0,0,0,0.6);
    position: relative;
  }
  #detail-close {
    position: absolute; top: 10px; right: 12px;
    background: none; border: none; color: #666;
    font-size: 1.3rem; cursor: pointer; line-height: 1; padding: 0;
  }
  #detail-close:hover { color: #ccc; }
  #detail-head { padding: 14px 16px 10px; border-bottom: 1px solid #2a2a4e; flex-shrink: 0; }
  #detail-title { font-size: 1rem; font-weight: 700; color: #fff; }

  #detail-board-area {
    display: flex; gap: 16px; align-items: flex-start;
    padding: 14px 16px; flex-shrink: 0;
  }
  #detail-board-grid {
    display: grid; grid-template-columns: repeat(8,1fr); grid-template-rows: repeat(8,1fr);
    width: 260px; height: 260px; flex-shrink: 0;
    border: 2px solid #444; border-radius: 3px; overflow: hidden;
  }
  #detail-board-grid .sq {
    display: flex; align-items: center; justify-content: center;
    font-size: 1.6rem; line-height: 1; user-select: none;
  }
  .sq.light { background: #f5e8c8; }
  .sq.dark  { background: #c8956b; }
  .wp { color: #111; text-shadow: 0 0 2px #fff, 0 0 3px #fff, 0 0 1px #fff; }
  .bp { color: #fff; text-shadow: 0 0 2px #000, 0 0 3px #000, 0 0 1px #000; }
  .sq.hl { outline: 3px inset #00d4ff; outline-offset: -3px; }

  #detail-board-right { display: flex; flex-direction: column; flex: 1; min-width: 0; gap: 10px; }
  #detail-move-seq { font-size: 0.85rem; color: #ddd; line-height: 1.9; word-break: break-word; }
  #detail-move-seq .mn { color: #555; }
  #detail-move-seq .mv { cursor: pointer; padding: 1px 3px; border-radius: 3px; }
  #detail-move-seq .mv:hover { background: #16213e; }
  #detail-move-seq .mv.current { background: #0f3460; color: #fff; font-weight: 700; }
  #detail-gap-msg { color: #dc3545; font-size: 0.85rem; padding: 14px 16px; }
  #detail-controls { display: flex; gap: 6px; }
  #detail-controls button { padding: 5px 10px; font-size: 0.8rem; }
</style>
</head>
<body>
<h1>ECO Opening Explorer</h1>
<div id="subtitle">Full ECO classification reference — independent of played games. Browse by volume/code, search by name, or sort by move sequence.</div>

<div id="top-bar">
  <div id="volume-tabs"></div>
  <div id="controls-row">
    <input id="search-input" type="text" placeholder="Search opening name…" autocomplete="off">
    <span id="sort-label">Sort:</span>
    <select id="sort-select">
      <option value="code">By code</option>
      <option value="name">By name</option>
      <option value="moves">By move sequence</option>
    </select>
  </div>
</div>

<div id="breadcrumb"></div>
<div id="list-summary"></div>
<div id="list-panel"></div>

<div id="detail-veil" onclick="closeDetail(event)">
  <div id="detail-modal">
    <button id="detail-close" onclick="closeDetail()">✕</button>
    <div id="detail-head">
      <div id="detail-title"></div>
    </div>
    <div id="detail-board-area">
      <div id="detail-board-grid"></div>
      <div id="detail-board-right">
        <div id="detail-move-seq"></div>
        <div id="detail-controls">
          <button onclick="stepStart()">⏮ Start</button>
          <button onclick="stepPrev()">◀ Prev</button>
          <button onclick="stepNext()">Next ▶</button>
          <button onclick="stepEnd()">End ⏭</button>
        </div>
      </div>
    </div>
    <div id="detail-gap-msg" style="display:none">Move sequence unavailable for this line.</div>
  </div>
</div>

<script>
const ECO_LINES = __ECO_LINES_JSON__;

const PIECES = {
  K:'♔',Q:'♕',R:'♖',B:'♗',N:'♘',P:'♙',
  k:'♚',q:'♛',r:'♜',b:'♝',n:'♞',p:'♟',
};
const VOLUMES = ['A','B','C','D','E'];

// ── Derived indices ─────────────────────────────────────────────────────
const byVolume = {};
const byCode = {};
for (const line of ECO_LINES) {
  const vol = line.eco ? line.eco[0] : '?';
  (byVolume[vol] = byVolume[vol] || []).push(line);
  (byCode[line.eco] = byCode[line.eco] || []).push(line);
}
const ALL_CODES = Object.keys(byCode).sort();

function codesForVolume(vol) {
  return vol ? ALL_CODES.filter(c => c[0] === vol) : ALL_CODES;
}

// ── State ────────────────────────────────────────────────────────────────
const state = { volume: '', code: '', search: '', sort: 'code' };

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function formatMoveText(moves) {
  if (!moves || !moves.length) return '<span class="gap-marker">(no move data)</span>';
  let out = '';
  for (let i = 0; i < moves.length; i++) {
    if (i % 2 === 0) out += `<span class="mn">${(i/2)+1}.</span>`;
    out += escapeHtml(moves[i]) + ' ';
  }
  return out.trim();
}

function compareByMoves(a, b) {
  const ma = a.moves || [], mb = b.moves || [];
  const n = Math.min(ma.length, mb.length);
  for (let i = 0; i < n; i++) {
    if (ma[i] < mb[i]) return -1;
    if (ma[i] > mb[i]) return 1;
  }
  return ma.length - mb.length;
}
function compareByCode(a, b) {
  return (a.eco || '').localeCompare(b.eco || '') || (a.name || '').localeCompare(b.name || '');
}
function compareByName(a, b) {
  return (a.name || '').localeCompare(b.name || '') || (a.eco || '').localeCompare(b.eco || '');
}

function isPrefixExtension(prev, cur) {
  const pm = prev.moves || [], cm = cur.moves || [];
  if (cm.length <= pm.length) return false;
  for (let i = 0; i < pm.length; i++) if (pm[i] !== cm[i]) return false;
  return true;
}

function searchMatches(q) {
  const needle = q.toLowerCase();
  return ECO_LINES.filter(l => (l.name || '').toLowerCase().includes(needle));
}

// Returns { kind: 'codes', items: [...] } or { kind: 'lines', items: [...] }
function getDisplayed() {
  if (state.sort === 'moves') {
    const base = state.search ? searchMatches(state.search) : ECO_LINES;
    const withMoves = base.filter(l => l.moves && l.moves.length);
    const withoutMoves = base.filter(l => !l.moves || !l.moves.length);
    withMoves.sort(compareByMoves);
    return { kind: 'lines', items: withMoves.concat(withoutMoves) };
  }
  if (state.search) {
    const items = searchMatches(state.search);
    items.sort(state.sort === 'name' ? compareByName : compareByCode);
    return { kind: 'lines', items };
  }
  if (state.code) {
    const items = (byCode[state.code] || []).slice();
    items.sort(state.sort === 'name' ? compareByName : compareByCode);
    return { kind: 'lines', items };
  }
  return { kind: 'codes', items: codesForVolume(state.volume) };
}

// ── Rendering ────────────────────────────────────────────────────────────
function renderVolumeTabs() {
  const el = document.getElementById('volume-tabs');
  const tabs = [['', 'All']].concat(VOLUMES.map(v => [v, v]));
  el.innerHTML = tabs.map(([v, label]) =>
    `<button class="vol-tab${state.volume === v ? ' active' : ''}" onclick="selectVolume('${v}')">${label}</button>`
  ).join('');
}

function selectVolume(vol) {
  state.volume = vol;
  state.code = '';
  state.sort = 'code';
  document.getElementById('sort-select').value = 'code';
  render();
}

function selectCode(code) {
  state.code = code;
  render();
}

function clearCode() {
  state.code = '';
  render();
}

function renderBreadcrumb(view) {
  const el = document.getElementById('breadcrumb');
  if (state.sort === 'moves') {
    el.innerHTML = state.search
      ? `<span class="crumb" onclick="clearSearchAndMoves()">All lines</span> — sorted by move sequence — matching "${escapeHtml(state.search)}"`
      : 'All lines, every volume — sorted by move sequence';
    return;
  }
  if (state.search) {
    el.innerHTML = `<span class="crumb" onclick="clearSearch()">Clear search</span> — results for "${escapeHtml(state.search)}"`;
    return;
  }
  const parts = [`<span class="crumb" onclick="selectVolume('')">All</span>`];
  if (state.volume) parts.push(`<span class="crumb" onclick="selectVolume('${state.volume}')">${state.volume}</span>`);
  if (state.code) parts.push(`<span>${state.code}</span>`);
  el.innerHTML = parts.join(' &rsaquo; ');
}

function clearSearch() {
  state.search = '';
  document.getElementById('search-input').value = '';
  render();
}
function clearSearchAndMoves() {
  state.search = '';
  document.getElementById('search-input').value = '';
  state.sort = 'moves';
  render();
}

function renderList() {
  const { kind, items } = getDisplayed();
  const summary = document.getElementById('list-summary');
  const panel = document.getElementById('list-panel');

  if (kind === 'codes') {
    summary.textContent = `${items.length} code${items.length !== 1 ? 's' : ''}`;
    if (!items.length) { panel.innerHTML = '<p class="none">No codes in this volume.</p>'; return; }
    let html = '<table><thead><tr><th>Code</th><th>Representative name</th><th class="count-cell">Lines</th></tr></thead><tbody>';
    for (const code of items) {
      const lines = byCode[code];
      const rep = lines.slice().sort((a, b) => (a.moves||[]).length - (b.moves||[]).length)[0];
      html += `<tr class="row-clickable" onclick="selectCode('${code}')">
        <td><span class="eco-badge">${code}</span></td>
        <td class="op-name">${escapeHtml(rep.name)}</td>
        <td class="count-cell">${lines.length}</td>
      </tr>`;
    }
    html += '</tbody></table>';
    panel.innerHTML = html;
    renderBreadcrumb();
    return;
  }

  // kind === 'lines'
  summary.textContent = items.length
    ? `${items.length} line${items.length !== 1 ? 's' : ''} matched`
    : '';
  currentItems = items;
  if (!items.length) {
    panel.innerHTML = '<p class="none">No matching lines found.</p>';
    renderBreadcrumb();
    return;
  }
  let html = '<table><thead><tr><th>Code</th><th>Name</th><th>Moves</th></tr></thead><tbody>';
  let prev = null;
  items.forEach(function (line, idx) {
    const isBreak = state.sort === 'moves' && prev && isPrefixExtension(prev, line) && prev.eco !== line.eco;
    const gap = (!line.moves || !line.moves.length) ? '<span class="gap-marker">(no move data)</span>' : '';
    const preview = (line.moves || []).slice(0, 6).join(' ') + ((line.moves||[]).length > 6 ? ' …' : '');
    html += `<tr class="row-clickable${isBreak ? ' seq-break' : ''}" data-idx="${idx}">
      <td><span class="eco-badge">${line.eco}</span></td>
      <td class="op-name">${escapeHtml(line.name)}${gap}</td>
      <td class="move-preview">${escapeHtml(preview)}</td>
    </tr>`;
    prev = line;
  });
  html += '</tbody></table>';
  panel.innerHTML = html;
  renderBreadcrumb();
}

let currentItems = [];
document.getElementById('list-panel').addEventListener('click', function (e) {
  const tr = e.target.closest('tr[data-idx]');
  if (!tr) return;
  const line = currentItems[Number(tr.dataset.idx)];
  if (line) openDetail(line);
});

function render() {
  renderVolumeTabs();
  renderList();
}

// ── Search / sort wiring ────────────────────────────────────────────────
document.getElementById('search-input').addEventListener('input', function () {
  state.search = this.value.trim();
  render();
});
document.getElementById('sort-select').addEventListener('change', function () {
  state.sort = this.value;
  if (state.sort === 'moves') {
    state.volume = '';
    state.code = '';
  }
  render();
});

// ── Board rendering (CSS grid, no external deps) ────────────────────────
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
function renderBoard(fen, uci, container) {
  const grid = fenToGrid(fen);
  container.innerHTML = '';
  const hlFrom = uci ? uci.slice(0, 2) : null;
  const hlTo = uci ? uci.slice(2, 4) : null;
  for (let r = 0; r < 8; r++) {
    for (let f = 0; f < 8; f++) {
      const sq = document.createElement('div');
      const sqName = String.fromCharCode(97 + f) + (8 - r);
      sq.className = 'sq ' + ((r + f) % 2 === 0 ? 'light' : 'dark');
      if (sqName === hlFrom || sqName === hlTo) sq.classList.add('hl');
      const p = grid[r][f];
      if (p) sq.innerHTML = `<span class="${p === p.toUpperCase() ? 'wp' : 'bp'}">${PIECES[p] || ''}</span>`;
      container.appendChild(sq);
    }
  }
}

// ── chess.js loader (SAN replay only — no chessboard.js/jQuery needed) ──
let chessJsState = 'idle'; // idle | loading | ready
let chessJsCallbacks = [];
function ensureChessJs(cb) {
  if (chessJsState === 'ready') { cb(); return; }
  chessJsCallbacks.push(cb);
  if (chessJsState === 'loading') return;
  chessJsState = 'loading';
  const s = document.createElement('script');
  s.src = 'https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js';
  s.onload = function () {
    chessJsState = 'ready';
    const cbs = chessJsCallbacks; chessJsCallbacks = [];
    cbs.forEach(f => f());
  };
  s.onerror = function () {
    document.getElementById('detail-gap-msg').textContent = 'Failed to load chess engine (internet required for step-through).';
    document.getElementById('detail-gap-msg').style.display = 'block';
  };
  document.head.appendChild(s);
}

// ── Line detail modal ────────────────────────────────────────────────────
let detailFens = [];
let detailUcis = [];
let detailStep = 0;

function openDetail(line) {
  document.getElementById('detail-title').innerHTML = `<span class="eco-badge">${line.eco}</span> ${escapeHtml(line.name)}`;
  document.getElementById('detail-veil').classList.add('open');
  const gapMsg = document.getElementById('detail-gap-msg');
  const boardArea = document.getElementById('detail-board-area');

  if (!line.moves || !line.moves.length) {
    boardArea.style.display = 'none';
    gapMsg.textContent = 'Move sequence unavailable for this line.';
    gapMsg.style.display = 'block';
    return;
  }
  gapMsg.style.display = 'none';
  boardArea.style.display = 'flex';
  document.getElementById('detail-move-seq').innerHTML = 'Loading…';

  ensureChessJs(function () {
    const chess = new Chess();
    const fens = [chess.fen()];
    const ucis = [null];
    for (const san of line.moves) {
      const mv = chess.move(san, { sloppy: true });
      if (!mv) break;
      fens.push(chess.fen());
      ucis.push(mv.from + mv.to);
    }
    detailFens = fens;
    detailUcis = ucis;
    renderMoveList(line.moves);
    jumpToStep(detailFens.length - 1);
  });
}

function closeDetail(e) {
  if (e && e.target !== document.getElementById('detail-veil')) return;
  document.getElementById('detail-veil').classList.remove('open');
}

function renderMoveList(moves) {
  const el = document.getElementById('detail-move-seq');
  let html = '';
  for (let i = 0; i < moves.length; i++) {
    if (i % 2 === 0) html += `<span class="mn">${(i/2)+1}.</span>`;
    html += `<span class="mv" data-step="${i+1}" onclick="jumpToStep(${i+1})">${escapeHtml(moves[i])}</span> `;
  }
  el.innerHTML = html;
}

function jumpToStep(i) {
  detailStep = Math.max(0, Math.min(i, detailFens.length - 1));
  renderBoard(detailFens[detailStep], detailUcis[detailStep], document.getElementById('detail-board-grid'));
  document.querySelectorAll('#detail-move-seq .mv').forEach(el => {
    el.classList.toggle('current', Number(el.dataset.step) === detailStep);
  });
}
function stepStart() { jumpToStep(0); }
function stepEnd() { jumpToStep(detailFens.length - 1); }
function stepPrev() { jumpToStep(detailStep - 1); }
function stepNext() { jumpToStep(detailStep + 1); }

document.addEventListener('keydown', function (e) {
  if (!document.getElementById('detail-veil').classList.contains('open')) return;
  if (e.key === 'Escape') { closeDetail(); return; }
  if (e.key === 'ArrowRight') { e.preventDefault(); stepNext(); }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); stepPrev(); }
});

render();
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the ECO Opening Explorer reference page")
    parser.add_argument("--eco-cache", default=str(DEFAULT_CACHE), help="Path to eco_openings.json (default: ./eco_openings.json)")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output HTML path (default: ./eco_explorer.html)")
    parser.add_argument("--refresh-cache", action="store_true", help="Force re-fetch upstream data even if the cache already has moves")
    args = parser.parse_args()

    cache_path = Path(args.eco_cache)
    out_path = Path(args.out)

    cache = augment_eco_cache(cache_path, force_refresh=args.refresh_cache)
    records = build_line_records(cache)
    write_page(records, out_path)


if __name__ == "__main__":
    main()
