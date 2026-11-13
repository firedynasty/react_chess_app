# Core board + move navigation

**Verdict: KEEP**

The board itself: load a PGN, step through moves, flip, sound, signals, opening toast, Hints modal.

**Entry point.** Always visible — the mini quick-access bar (index.html:1484-1528) and the control row below the board (index.html:1563-1626).

**Footprint.** 23 buttons · 95 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**localStorage.** `chessSoundEnabled` · `boardBorderEnabled` · `variationArrowsEnabled`

**Other files.** `chess.min.js` · `analysis_chess.js` · `src/stockfish-17.1-lite-single-03e3232.js (+ .wasm)`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 861 | `analyzeBtn` | Analyze Game | `analyzeGame` |
| 863 | `—` | Hints | `openHintsModal` |
| 865 | `copyPgnBtn` | Copy PGN | `async @13497` |
| 866 | `—` | Clear | `clearResults` |
| 1483 | `toggleNavBtnsBtn` | ▶ Show Nav Buttons | `getElementById, getElementById` |
| 1501 | `loadToBoardMini` | Load to Board | `loadPgnToBoard` |
| 1510 | `toggleSoundBtnMini` | Sound On | `toggleChessSound` |
| 1511 | `toggleBorderBtnMini` | Signals On | `toggleBoardBorder` |
| 1515 | `—` | Lichess Links | `proxy → `#lichessLinksBtn`` |
| 1516 | `showOpeningBtn` | 📖 Opening | `showOpeningToast` |
| 1517 | `—` | Reanalyze | `proxy → `#analyzeGameBtn`` |
| 1519 | `copyBoardPgnBtnMini` | Copy PGN | `copyPgnToClipboard` |
| 1527 | `—` | Hints | `openHintsModal` |
| 1532 | `—` | ✕ *(~inherited)* | `getElementById` |
| 1603 | `copyBoardPgnBtn` | Copy PGN | `copyPgnToClipboard` |
| 1604 | `downloadPgnBtn` | Download PGN | `downloadPgn` |
| 1609 | `lichessLinksBtn` | Lichess Links | `function @13453` |
| 1610 | `toggleChatBtn` | Toggle Chat | `getElementById` |
| 1611 | `toggleSoundBtn` | Sound On | `toggleChessSound` |
| 1612 | `toggleBorderBtn` | Signals On | `toggleBoardBorder` |
| 1615 | `toggleMoveTableBtn` | Hide Moves | `function @13531` |
| 1616 | `toggleAddVarBtn` | Add Var | `getElementById, gradient` |
| 1693 | `—` | ✕ | `getElementById` |

## Notes

- This is the one thing everything else hangs off. Nothing here goes.
- But see `duplicate-controls.md` — a third of these buttons exist twice.

## Culled

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
