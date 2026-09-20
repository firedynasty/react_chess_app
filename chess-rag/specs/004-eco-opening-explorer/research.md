# Phase 0 Research: ECO Opening Explorer

## 1. Where do move sequences come from?

**Decision**: Re-fetch `eco{A-E}.json` from `https://raw.githubusercontent.com/hayatbiralem/eco.json/master/eco{letter}.json` (same URL `tree_viz.py:150` already uses) and read each entry's `moves` field (upstream format is `{fen: {"eco": "...", "name": "...", "moves": "1. e4 c6"}}`), rather than deriving move sequences ourselves by replaying every possible line.

**Rationale**: `tree_viz.py`'s `load_eco_data()` already discards the `moves` field on ingest (`load_eco_data()` at `tree_viz.py:159-192` only keeps `eco`/`name` per entry) — the data was always there, it was just never persisted to `eco_openings.json`. Re-running the same fetch and keeping the extra field is the minimal change; no new upstream dependency.

**Alternatives considered**:
- *Derive moves by exhaustive tree search over all legal openings* — rejected, reinvents what the upstream classification already encodes, and risks producing a different move order (transposition) than the canonical one users expect from ECO references.
- *Use `python-chess`'s built-in opening book / polyglot data* — rejected, doesn't carry ECO names/codes in the form this project already standardized on.

**Fallback if upstream field is absent/renamed on a given entry**: skip storing `moves` for that entry only (never fail the whole build) and mark it in the generated page per FR-009 ("data gap" — shown, but flagged as having no playable sequence), consistent with the spec's edge case for missing move data.

## 2. How to compute per-ply board positions for step-through (FR-005)?

**Decision**: Store only the final FEN + the SAN move array per line in the cache/embedded data (as already done for `opening_fen` / `opening_moves` on played games in `tree_viz.py:236-252`). At render time in the browser, replay the SAN array with `chess.js` (already loaded on-demand via `ensureChessLibs()` in `tree_viewer.html`) to produce the FEN after each ply, exactly as `pgnParseTokens` does for real games (`tree_viewer.html:1408-1448`).

**Rationale**: Avoids ~5-10x data bloat from storing an intermediate FEN per ply for 12,000 lines; `chess.js` replay of a short, unambiguous SAN sequence (no variations, no comments — unlike full PGN parsing) is trivial and fast. Reuses a library and pattern already proven in this codebase rather than introducing a second replay implementation.

**Alternatives considered**:
- *Precompute and store all per-ply FENs in the data file* — rejected as unnecessary data size for a page that's meant to stay a single static file.
- *Use `python-chess` to precompute per-ply FENs server-side instead of `chess.js` client-side* — rejected; would need to store them anyway (same size cost) or recompute them on every generator run, and duplicates logic already solved client-side.

## 3. How to render the board and detail panel (FR-005)?

**Decision**: Reuse the existing lightweight CSS-grid board renderer (`renderBoard()` / `fenToGrid()`, `tree_viewer.html:571-608`) and the opening-detail-modal layout (`openOpModal()`, `tree_viewer.html:930-1020` — badge/name header, board, move sequence), not the `chessboard.js`-based PGN modal, and not that modal's copy-position control (dropped — this feature has no tie to played-game data). Add step controls (`Start`/`Prev`/`Next`/`End` buttons + Left/Right arrow keys, modeled directly on `pgnGoStart`/`pgnGoPrev`/`pgnGoNext`/`pgnGoEnd`/`pgnJump` at `tree_viewer.html:1480-1493`) driving the CSS-grid board instead of a `chessboard.js` instance.

**Rationale**: FR-005 explicitly requires "matching the look of the existing per-opening detail view elsewhere in chess-rag (board + move list together)" — that view is `openOpModal`, which already uses the CSS-grid board, not `chessboard.js`. Keeping the same renderer avoids pulling in `chessboard.js` (and its piece-image CDN dependency) for a page that has no drag-and-drop needs.

**Alternatives considered**:
- *Use `chessboard.js` (as the PGN modal does)* — rejected; heavier dependency (external piece image CDN) for no benefit since this page never needs draggable pieces.

## 4. How to sort by move sequence (FR-010, SC-005)?

**Decision**: This is nothing more than a plain sort — sort all lines by their SAN move array as a tuple/lexicographic key (element-wise comparison; a shorter sequence sorts immediately before any sequence that extends it). No continuation graph, no relationship data, no cross-referencing step. The "continuations stay adjacent across codes" behavior (e.g. `["d4","d5","c4","c6"]` → `["d4","d5","c4","c6","Nf3"]` → `["d4","d5","c4","c6","Nf3","Nf6","Nc3","e6"]` land in consecutive rows) falls out automatically from this sort key alone.

**Rationale**: Tuple/array comparison of move sequences has the exact property wanted: if line A's moves are a strict prefix of line B's moves, A sorts immediately before B. That's the entire mechanism — confirmed with the user as the intended behavior (they described it themselves as "x x x, then x x x d below it, then x x x d e"). No graph/tree data structure is built.

**Alternatives considered**:
- *Build an explicit continuation graph/tree (parent/child links across codes) and render it as a tree view* — rejected as unnecessary; the user explicitly does not want this feature tied to any game/relationship modeling, just a straightforward sort. Would also visually collide with FR-006's requirement to look distinct from the existing played-games *tree* view.
- *Group by common opening-name prefix instead of moves* — rejected; two lines can share a family name without one being a true move-sequence extension of the other (and vice versa), so name-based grouping wouldn't reliably nest continuations the way move-sequence sorting does.

## 5. How to keep codes with 200+ lines navigable (Edge Case, FR-008)?

**Decision**: No server-side pagination (ruled out by the spec's Assumption re: client-side scale). Render a fixed-height, scrollable list panel per code, with the in-page name search box also active *within* a selected code (so typing narrows the current code's list, not just the global search). A visible "N lines" count (FR-008) sits above the list at all times — for both a browsed code and a search result.

**Rationale**: Matches the spec's own suggested mechanisms ("grouped, paginated, or scrollable") at the cheapest implementation cost, and reuses the same search input for both global (User Story 2) and in-code narrowing rather than building two separate filter UIs.

**Alternatives considered**:
- *Virtualized/windowed list rendering* — rejected as premature; 200 rows of simple text is not a real rendering-performance problem in any modern browser, so virtualization would be complexity without a measured need.

## 6. Where does the generated page live, and how is data embedded?

**Decision**: `chess-rag/eco_explorer.py` generates `chess-rag/eco_explorer.html` at the repo root (sibling to `eco_openings.json`), using the same `HTML_TEMPLATE` string + placeholder-`replace()` pattern `tree_viz.py` uses for `TREE`/`PGNS` (`tree_viz.py:746-747, 1918-1927`) — e.g. `const ECO_LINES = __ECO_LINES_JSON__;`.

**Rationale**: Every other generated gallery in this repo (`tree_viewer.html`, and the video/image galleries per the top-level `CLAUDE.md`) follows "processing script → embedded/generated JS data → static HTML," so this keeps the new feature consistent with the project's existing authoring model instead of introducing a build step, bundler, or server route.

**Alternatives considered**:
- *Serve the reference data via a new `/api/eco-lines` endpoint (mirroring `/api/games`)* — rejected; the spec explicitly frames this as an offline-capable reference (Edge Cases: "What happens when the user is offline...") and the dataset is static/rarely-changing, so a live API adds a runtime dependency for no benefit over a baked-in JSON literal.
