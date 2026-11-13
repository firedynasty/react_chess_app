# Save → Puzzles (single position)

**Verdict: MERGE into puzzles-transfer**

Save the move's position, a bare FEN, or the whole game into the puzzles table from a modal.

**Entry point.** `Save → Puzzles` (index.html:1526) opens `#pzSaveModal`.

**Footprint.** 7 buttons · 97 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**API.** `/api/puzzles`

**Other files.** `api/puzzles.js` · `puzzles.html`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1077 | `—` | 📋 Copy PGN | `pzCopyPgn` |
| 1078 | `—` | 📥 Paste PGN | `pzPastePgn` |
| 1079 | `—` | 🗑️ Clear PGN | `pzClearPgn` |
| 1080 | `—` | ↺ Reset FEN | `pzResetPgnFen` |
| 1525 | `savePuzzleBtnMini` | Save → Puzzles | `openPuzzleSaveModal` |
| 1822 | `—` | ✕ | `closePuzzleSaveModal` |
| 1835 | `pzSaveBtn` | Save to puzzles | `pzSave` |

## Notes

- Same destination table as `puzzles-transfer` and as Practice's `Save to puzzles` (index.html:1810) — three doors into one table.
- Pick one. The modal (`pzSave`) is the most capable; delete `practiceSave` and point Practice's button at it.
