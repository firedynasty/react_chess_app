# Core board + move navigation

**Verdict: KEEP**

The board itself: load a PGN, step through moves, flip, sound, signals, opening toast, Hints modal.

**Entry point.** Always visible — the mini quick-access bar (index.html:1467-1513) and the control row below the board (index.html:1547-1611).

**Footprint.** 22 buttons · 95 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**localStorage.** `chessSoundEnabled` · `boardBorderEnabled` · `variationArrowsEnabled`

**Other files.** `chess.min.js` · `analysis_chess.js` · `src/stockfish-17.1-lite-single-03e3232.js (+ .wasm)`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 858 | `analyzeBtn` | Analyze Game | `analyzeGame` |
| 860 | `—` | Hints | `openHintsModal` |
| 861 | `—` | Clear | `clearResults` |
| 1468 | `toggleNavBtnsBtn` | ▶ Show Nav Buttons | `getElementById, getElementById` |
| 1486 | `loadToBoardMini` | Load to Board | `loadPgnToBoard` |
| 1495 | `toggleSoundBtnMini` | Sound On | `toggleChessSound` |
| 1496 | `toggleBorderBtnMini` | Signals On | `toggleBoardBorder` |
| 1500 | `—` | Lichess Links | `proxy → `#lichessLinksBtn`` |
| 1501 | `showOpeningBtn` | 📖 Opening | `showOpeningToast` |
| 1502 | `—` | Reanalyze | `proxy → `#analyzeGameBtn`` |
| 1504 | `copyBoardPgnBtnMini` | Copy PGN | `copyPgnToClipboard` |
| 1512 | `—` | Hints | `openHintsModal` |
| 1517 | `—` | ✕ *(~inherited)* | `getElementById` |
| 1588 | `copyBoardPgnBtn` | Copy PGN | `copyPgnToClipboard` |
| 1589 | `downloadPgnBtn` | Download PGN | `downloadPgn` |
| 1594 | `lichessLinksBtn` | Lichess Links | `function @12803` |
| 1595 | `toggleChatBtn` | Toggle Chat | `getElementById` |
| 1596 | `toggleSoundBtn` | Sound On | `toggleChessSound` |
| 1597 | `toggleBorderBtn` | Signals On | `toggleBoardBorder` |
| 1600 | `toggleMoveTableBtn` | Hide Moves | `function @12856` |
| 1601 | `toggleAddVarBtn` | Add Var | `getElementById, gradient` |
| 1678 | `—` | ✕ | `getElementById` |

## Notes

- This is the one thing everything else hangs off. Nothing here goes.
- But see `duplicate-controls.md` — a third of these buttons exist twice.

## Culled

- **`copyPgnBtn` "Copy PGN"** — removed, the one in the paste-PGN row above `Clear`. Element was
  at `index.html:861`; binding block and anonymous handler at `index.html:12845-12868` (24 lines).
  The handler was an inline closure, so nothing else could call it; no `window` export, no
  localStorage, no shortcut, and the only reads of the id were its own "Copied!" / "No PGN!" /
  "Failed" text flashes inside that closure.
  Redundant with three other `Copy PGN` buttons: `copyBoardPgnBtnMini` (`1504`, mini bar),
  `copyBoardPgnBtn` (`1588`, control row) — both `copyPgnToClipboard()` — and `coachPgnCopyBtn`
  in the coach modal.
  **One behaviour went with it.** This button was the only one that fell back to the raw
  `#pgnInput` textarea when `window.moveTree` was null, so "paste a PGN, copy it straight back
  out without loading it" is gone. `copyPgnToClipboard()` falls back to `window.currentLoadedPgn`
  / `window.annotatedPgnWithVariations` instead and logs *No PGN available to copy* when neither
  is set. The textarea's text is still selectable by hand.
  Also dropped `copyPgnBtn` from the `core-board` RULES pattern; the other two classify through
  `copyPgnToClipboard`.

- **`loadToBoard` "Load to Board"** — removed. Element was at `index.html:863` in the paste-PGN
  button row; binding block at `index.html:13496-13500` (comment + `const` alias + `if` guard +
  `addEventListener`). No `window` export, no localStorage, no keyboard shortcut, and the only
  references to the id anywhere were the three lines of its own binding block, so nothing outside
  could reach it.
  Redundant with **`loadToBoardMini`** (`index.html:1501`) in the always-visible mini bar, which
  calls the same `loadPgnToBoard()` via an inline `onclick` and whose own tooltip says
  "same as Load to Board". The paste → Load to Board workflow is unchanged; the surviving button
  reads the same `#pgnInput` textarea (and falls back to the clipboard when it is empty).
  `loadPgnToBoard()` **stays** — besides `loadToBoardMini` it has three other call sites
  (`index.html:3056`, `14348`, `17425`, pre-delete numbering).
  Also dropped `loadToBoard` from the `core-board` RULES pattern in `extract_buttons.py`;
  `loadToBoardMini` still classifies through `loadPgnToBoard` in its `onclick`.
  Closes the **load to board** pair in [duplicate-controls.md](duplicate-controls.md).

- **`loadCurrentBtn` "Load Current"** — removed. Element was at `index.html:863`; binding and
  anonymous handler at `index.html:13496-13535` (40 lines). No `window` export, no localStorage,
  no shortcut; the only other references to the id were inside its own handler (the "Loaded!"
  text flash), so nothing outside could call it.
  Redundant: `<select id="game-dropdown" onchange="loadSelectedGame()">` (`index.html:818`) and
  `loadSelectedGame()` (was `index.html:9795`) already write the selected game's PGN into
  `#pgnInput`. The button was a manual re-run of that.
  It also belonged here only by accident — it read `#game-dropdown` and `window.fetchedGames`,
  both populated solely by the fetchers in [02-game-sources.md](02-game-sources.md).
  The shared functions it called (`clearResults`, `moveTreeToPgn`, `clearBoard2Arrows`,
  `updateEvalBar`) have other callers and were left alone.
