# Chess Game Analyzer — Portfolio Showcase

A fully client-side chess analysis web application. No backend required for analysis — everything runs in the browser.

**Live:** Deployed on Vercel | **Stack:** Vanilla JS, WebAssembly, Chess.js, Chessboard.js, Google Drive API, Dropbox API, Chess.com API

---

## Headline Features

### Stockfish 17.1 NNUE in the Browser
- Runs Stockfish 17.1 with neural network evaluation (NNUE) entirely client-side via WebAssembly
- ~7MB lite-single build — no server, no SharedArrayBuffer headers required, works on any static host
- Communicates over the UCI protocol using the Web Worker API
- Custom `analyzePosition()` with `addEventListener`/`removeEventListener` isolation per call (eliminates race conditions from queued messages)
- Single-pass White's-perspective eval loop with `prevEval` carry-forward (eliminates false blunders on check/forced positions)
- Won-position filter (±600cp) with missed-mate exception — flags `Qd6#` if the player played a non-mate move instead

### Full Game Analysis Pipeline
- Detects **blunders** (≥200cp loss), **mistakes** (≥100cp loss) for every move in a game
- Stores per-FEN evaluations in `window.positionEvalMap` — feeds the live eval bar as you navigate
- Auto-generates Stockfish best-move variations for each detected blunder/mistake, inserted into the PGN move tree with arrows
- Supports Chessis-annotated PGNs (`{Best: move}` comments) — extracts best moves from comments and runs the same variation pipeline
- **Load Current** button re-loads a saved game clean (strips variations) and auto-triggers analysis after 500ms

### Interactive Move Tree & Board
- Full PGN move tree with variation branches — not a flat array
- `jumpToNode()` / `jumpToRoot()` tree navigation with smooth scroll to current move in the move table
- SVG arrow overlays drawn on the board for variation best moves
- Board opacity dims when viewing a variation (visual cue you're off the mainline)
- `Cycle Var.` button cycles through multiple variations at a branch point
- Horizontal eval bar with **tanh scaling** (`50 + tanh(cp/400) * 50`) — smooth S-curve that handles extreme evals without hard clamping, animates on every move navigation
- **Get Eval** button traverses the full move tree, analyzes each position at depth 12, fills the eval map for any loaded PGN

### Chess.com API Integration
- Fetches current + previous month games for any username via the Chess.com public API
- Extracts ECO code, opening name, opponent, rating, result, time class, game URL
- Parses and strips PGN headers automatically — feeds clean move text into the analysis pipeline

### Google Drive / Sheets Integration
- OAuth2 authentication to Google Drive
- Loads `.xlsx` spreadsheets via the Drive API, parsed in-browser with XLSX.js
- Row navigation (↑/↓) with preview (col1, col2, first 100 chars of col3)
- Save analyzed games back to the sheet: col1 = title, col2 = notes, col3 = annotated PGN
- Auto-fills col3 from the current board PGN if left blank on save

### Dropbox Integration
- PKCE OAuth flow (no client secret exposed)
- In-browser folder navigation with search
- Save/load analysis reports as `.txt` files
- Nested folder traversal with back navigation

### Annotated PGN Pipeline
- `parsePgnWithVariations()` — full recursive PGN parser handling nested variations, NAG codes, comments
- `moveTreeToPgn()` — serializes the move tree back to valid PGN with variations
- `addVariationToPgn()` — inserts a Stockfish PV line at the correct ply in the tree
- `updateReportWithPgn()` — syncs the annotated PGN section of the text report after any tree change
- Insert variations by pasting PGN — auto-detects insertion point from FEN match

### Analysis Report
- Auto-generated structured text report: opening, stats, blunder/mistake breakdown with centipawn values, full EVAL DEBUG LOG (per-move `evalBefore → evalAfter swing [status]`), annotated PGN, Lichess puzzle recommendations
- Toggle show/hide (hidden by default), edit mode for manual annotation
- Save to local file or Dropbox
- `Load Annotated PGN` — paste any PGN from clipboard onto the board

---

## Technical Highlights

| Area | Implementation |
|------|---------------|
| Chess engine | Stockfish 17.1 NNUE, WebAssembly, Web Worker |
| Eval scaling | tanh curve — smooth, no hard clamp at extreme values |
| False blunder prevention | Single-pass prevEval carry-forward + won-position filter + missed-mate exception |
| PGN parsing | Hand-written recursive descent parser for nested variations |
| Move tree | Node graph with parent pointers, nodeId registry, O(1) lookup |
| Auth | Google OAuth2 + Dropbox PKCE (no backend) |
| Deployment | Fully static — Vercel, GitHub Pages, any CDN |
| Engine loading | No SharedArrayBuffer needed — lite-single WASM build |

---

## What Makes It Non-Trivial

- **No server for analysis.** Stockfish 17.1 NNUE runs in the browser. Most chess tools offload analysis to a server. This app scales infinitely — each user runs their own engine instance.
- **Correct blunder detection is hard.** The naive approach (store evals, compare pairs) produces false blunders on check positions where Stockfish returns 0.00 before completing the search. The fix (single-pass carry-forward, `addEventListener` isolation, won-position filter) took significant debugging to get right. Documented in `stockfish-implementation.md`.
- **PGN with nested variations is a recursive data structure.** Writing a parser and serializer for it from scratch — and keeping the move tree consistent after insertions — is the core engineering challenge of the app.
- **Three separate OAuth flows** (Chess.com public, Google Drive, Dropbox PKCE) all coordinated in a single-page app with no build step.

---

## Files of Note

| File | Purpose |
|------|---------|
| `index.html` | Entire application (~9600 lines, no build step) |
| `src/stockfish-17.1-lite-single-*.js/.wasm` | Stockfish 17.1 NNUE engine |
| `stockfish-implementation/stockfish-implementation.md` | Engineering notes on Stockfish.js bugs and fixes |
| `research-stockfish.md` | GitHub repos and patterns studied during development |
| `research-stockfish-nnue.md` | NNUE upgrade research and build comparison |
| `future-implementation.md` | Planned improvements with rationale |
| `hidden-features/` | Archived UI components available for restoration |
