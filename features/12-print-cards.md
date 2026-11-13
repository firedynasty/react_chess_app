# Print list + Print Line (study cards)

**Verdict: MERGE — two modals into one**

Collect positions and print them as front/back study cards, 8 per sheet; or paste one line and print its boards 2x4.

**Entry point.** `+ For Print (0)` (1505) · `⚡ 1 shot` (1506) · `Print Line` (1509) · `Print List` (1510), modals `#ppAddModal` `#ppLineModal` `#ppListModal`.

**Footprint.** 29 buttons · 144 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**localStorage.** `chessPrintDropboxPath`

**Other files.** `puzzles.html` · `animatedFlashcards/` · `api/dropbox-config.js`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1504 | `ppAddBtn` | + For Print (0) | `ppOpenAdd` |
| 1505 | `ppOneShotBtn` | ⚡ 1 shot | `ppOneShot` |
| 1508 | `ppLineBtn` | Print Line | `ppOpenLine` |
| 1509 | `ppListBtn` | Print List | `ppOpenList` |
| 18869 | `—` | ✕ | `ppCloseAdd` |
| 18874 | `ppMovesToggle` | ▸ Choose a position from the moves | `ppToggleMoves` |
| 18877 | `—` | ⚡ Fill back from the better line ↓ | `ppFillBetter` |
| 18880 | `—` | Add | `ppConfirmAdd` |
| 18881 | `—` | Cancel | `ppCloseAdd` |
| 18887 | `—` | ✕ | `ppCloseLine` |
| 18896 | `—` | ↻ Redraw the boards | `ppLineChanged` |
| 18897 | `—` | ＋ Add to the set | `ppLineAddToSet` |
| 18902 | `ppLineFlipBtn` | White at bottom | `ppLineFlip` |
| 18903 | `—` | Restore removed | `ppLineRestore` |
| 18904 | `—` | 🖨 Print | `ppLinePrint` |
| 18905 | `ppLinePrintSetBtn` | 🖨 Print set (0) | `ppLinePrintSet` |
| 18913 | `—` | ✕ | `ppCloseList` |
| 18918 | `—` | ⚡ Pick from this game's mistakes | `ppAutoFill` |
| 18924 | `—` | 🖨 Print | `ppPrint` |
| 18925 | `ppClearBtn` | Clear all | `ppClear` |
| 18928 | `—` | ⬇ Export JSON | `ppExportJson` |
| 18929 | `—` | ⬆ Load JSON (replaces) | `proxy → `#ppLoadFile`` |
| 18935 | `—` | ☁ Save to Dropbox | `ppDbxSave` |
| 18936 | `—` | ☁ Load from Dropbox (replaces) | `ppDbxLoad` |
| 19116 | `—` | ✕ | `ppRemove` |
| 19185 | `—` | Select all | `ppAutoAll` |
| 19186 | `—` | Add selected | `ppAutoAdd` |
| 19187 | `—` | Close | `getElementById` |
| 19434 | `—` | ✕ | `ppLineRemove` |

## Notes

- Three modals, 29 buttons, two Print buttons (18945 and 18965), two Export JSON buttons (18969 and features/pgn-library 2092), and a Dropbox save/load pair on top.
- `ppLine*` (paste a line → print its boards) is a strict subset of what `ppList*` already does with a one-entry set. Fold it in; that is ~11 buttons and one modal gone.
- Also drop `fen-export`'s `fenQueue*` CSV queue — it is the pre-Print-List version of this same idea.
