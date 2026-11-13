# FEN export, FEN queue, board images

**Verdict: CUT the queue**

Export the board FEN for white/black, copy it, queue FENs and download them as CSV, download board images, load a FEN from a modal.

**Entry point.** `Export FEN` (1508 and 1610) · `#fenExportModal` (1862-1893) · `Download Images` (1621) · `Load FEN` (1608) · `#loadFenModal`.

**Footprint.** 16 buttons · 80 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**localStorage.** `fenPuzzleQueue`

**Other files.** `fenBuilder.html` · `loadfromfen_build_textarea.js`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 862 | `analyzeFenBtn` | Analyze Position **(hidden)** | `analyzeFen` |
| 1507 | `exportFenBtnMini` | Export FEN | `proxy → `#exportFenBtn`` |
| 1607 | `loadFenBtn` | Load FEN | `function @12945` |
| 1608 | `fenColorToggleBtn` | White | `function @13294` |
| 1609 | `exportFenBtn` | Export FEN | `function @13395` |
| 1620 | `downloadBoardImagesBtn` | Download Images | `downloadBoardImages` |
| 1861 | `—` | ✕ | `getElementById` |
| 1869 | `—` | Copy White FEN | `copyExportedFen` |
| 1877 | `—` | Copy Black FEN | `copyExportedFen` |
| 1886 | `—` | + Add White FEN | `fenQueueAddWhite` |
| 1887 | `—` | + Add Black FEN | `fenQueueAddBlack` |
| 1888 | `—` | Download CSV | `fenQueueDownload` |
| 1892 | `—` | Clear queue | `fenQueueClear` |
| 1927 | `—` | ✕ | `getElementById` |
| 1932 | `—` | Cancel | `getElementById` |
| 1933 | `—` | Load | `submitLoadFenModal` |

## Notes

- `fenQueue*` (`+ Add White FEN`, `+ Add Black FEN`, `Download CSV`, `Clear queue`) is the ancestor of Print List. Nothing points at it from the main bar any more.
- Keep `Export FEN` and `Load FEN` — they are the manual escape hatch. Delete the queue and `fenPuzzleQueue`.
