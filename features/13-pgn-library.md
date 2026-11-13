# PGN Library sidebar

**Verdict: CUT**

Load a JSON of games or a folder of .pgn/.txt files and browse them in a sidebar with Prev/Next.

**Entry point.** `📚 Library` (index.html:1528) → the panel at index.html:2087-2099.

**Footprint.** 7 buttons · 13 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**Other files.** `build_pgn_library.py` · `saved_games/`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1527 | `pgnLibBtnMini` | 📚 Library | `plToggle` |
| 2086 | `—` | × | `plToggle` |
| 2089 | `—` | ⬆ Load JSON | `proxy → `#plJsonInput`` |
| 2090 | `—` | 📁 Load folder | `proxy → `#plFolderInput`` |
| 2091 | `—` | ⬇ Export JSON | `plExportJson` |
| 2097 | `—` | ◀ Prev | `plStep` |
| 2098 | `—` | Next ▶ | `plStep` |

## Notes

- Seven buttons, and it is the eleventh way to get a game onto the board. Its `⬇ Export JSON` (2092) duplicates print-cards' (18969).
- The Dropbox PGN loader this note used to recommend keeping is gone ([15-dropbox.md](15-dropbox.md)), so if you keep a file-based loader at all, it is this one or nothing.
