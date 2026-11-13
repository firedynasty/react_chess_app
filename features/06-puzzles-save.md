# Save → Puzzles (single position)

**Verdict: MERGE into puzzles-transfer**

Save the move's position, a bare FEN, or the whole game into the puzzles table from a modal.

**Entry point.** `Save → Puzzles` (index.html:1510) opens `#pzSaveModal`.

**Footprint.** 3 buttons · 97 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**API.** `/api/puzzles`

**Other files.** `api/puzzles.js` · `puzzles.html`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1510 | `savePuzzleBtnMini` | Save → Puzzles | `openPuzzleSaveModal` |
| 1807 | `—` | ✕ | `closePuzzleSaveModal` |
| 1820 | `pzSaveBtn` | Save to puzzles | `pzSave` |

## Notes

- The four `#pzPgnSection` buttons this file used to list were never part of this feature — see
  `## Culled`.
- Same destination table as `puzzles-transfer` and as Practice's `Save to puzzles` (index.html:1810) — three doors into one table.
- Pick one. The modal (`pzSave`) is the most capable; delete `practiceSave` and point Practice's button at it.

## Culled

- **The `#pzPgnSection` button row — `📋 Copy PGN` (`pzCopyPgn`), `📥 Paste PGN` (`pzPastePgn`),
  `🗑️ Clear PGN` (`pzClearPgn`), `↺ Reset FEN` (`pzResetPgnFen`)** — removed. Elements were the
  flex row at `index.html:1074-1080`; the four handlers at `index.html:6370-6398`. 36 lines.
  Each was referenced exactly twice — its own inline `onclick` and its definition. No `window.`
  export, no localStorage, no shortcut, no other caller.

  **They never belonged to this feature.** They are not in `#pzSaveModal`; they sat in
  `#pzPgnSection` (`index.html:1072-1082`), the always-visible box holding the Lichess
  "From Position" PGN of moves you drop on the board. They were filed here only because the
  `pz` prefix matched the `puzzles-save` RULES pattern — the same trap the README warns about
  under `~inherited`, except this one came from the id, so it was not even marked as a guess.

  **Kept:** `#pzMoveHistoryTextArea` itself, and the drop handler + `pzRenderPgn()`,
  `window.pzPgnBase` and `pzIsAncestorOrSelf()` that write into it — they have other callers and
  the box still fills as you drop moves. It is now read-only display: `readonly` was already on
  the textarea, so with the row gone the text is select-and-copy by hand. `window.pzPgnBase` is
  never reset to `null` any more, which was `pzClearPgn`'s only job.
