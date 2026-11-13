# Study tool: board2 + analysis report

**Verdict: CUT most of it**

The older second board and its report system: load an analysis report from the clipboard, parse it into sections, load preloaded reports, append reports by opening, edit/save them, step FEN/PGN variants, append variants back.

**Entry point.** `Show Report` (999) · `Load Analysis Report (from clipboard)` (1172) · `📂 Select Reports Folder` (1176) · `📋 Preloaded Reports` (1178) · `📋 View Reports` (1180) · `📚 Append Opening Reports` (1184) · `Parse Report` (1948) · plus the board2 row at 1564-1627.

**Footprint.** 39 buttons · 1010 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**API.** `/api/game-report`

**Other files.** `preloaded_reports/` · `preloaded/` · `react-chat-report-viewer/` · `reducedHtml_chess-study-tool/` · `documentation/` · `report_div.txt` · `previous_analyze_game.js`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 998 | `toggleReportBtn` | Show Report | `function @12456` |
| 1034 | `loadPgnFromHighlight` | Load PGN from Highlight **(hidden)** | `function @15362` |
| 1035 | `loadFenVariantFromHighlight` | Load [Fen Variant] from Highlight **(hidden)** | `function @15403` |
| 1036 | `copyReportText` | Copy Text | `function @15440` |
| 1037 | `saveReportBtn` | 💾 Save Report | `function @14734` |
| 1039 | `editViewToggleBtn` | Edit | `function @14653` |
| 1055 | `—` | Append to Report | `pasteIntoReport` |
| 1059 | `—` | 📋 Paste from Clipboard | `readText, then, getElementById` |
| 1063 | `—` | Clear | `getElementById` |
| 1171 | `loadAnalysisReport` | Load Analysis Report (from clipboard) | `async @14398` |
| 1175 | `selectReportFolder` | 📂 Select Reports Folder | `proxy → `#reportFolderInput`` |
| 1177 | `loadPreloadedReports` | 📋 Preloaded Reports **(hidden)** | `async @14444` |
| 1179 | `viewPreloadedReports` | 📋 View Reports **(hidden)** | `openReportFilesModal @14502` |
| 1183 | `appendByOpeningBtn` | 📚 Append Opening Reports **(hidden)** | `async @14567` |
| 1374 | `fileSectionPrev` | ◀ | `function @14243` |
| 1380 | `fileSectionNext` | ▶ | `function @14255` |
| 1411 | `board2CompactBtn` | ⊡ Small | `toggleBoard2Compact` |
| 1488 | `—` | ← Prev | `proxy → `#board2PrevMove`` |
| 1489 | `—` | Next → | `proxy → `#board2NextMove`` |
| 1515 | `—` | Flip Board | `proxy → `#flip_board2`` |
| 1519 | `getEvalBtnMini` | Get Eval | `proxy → `#getEvalBtn`` |
| 1563 | `flip_board2` | Flip Board | `function @13530` |
| 1568 | `board2PrevMove` | ← Prev | `board2PrevMove @12823` |
| 1570 | `board2NextMove` | Next → | `board2NextMove @12818` |
| 1581 | `loadClipboardPgnBtn` | Load Annotated PGN | `async @12848` |
| 1582 | `loadFullReportBtn` | Load Report | `async @12887` |
| 1583 | `analyzeGameBtn` | Analyze Game | `analyzeLoadedGame` |
| 1584 | `getEvalBtn` | Get Eval | `getEvalForLoadedPgn @12842` |
| 1585 | `copyEvalsBtn` | 📋 Copy Evals | `copyEvalsForPaste` |
| 1595 | `prevVariant` | ← Prev FEN/PGN **(hidden)** | `function @14209` |
| 1596 | `nextVariant` | Next FEN/PGN → **(hidden)** | `function @14226` |
| 1606 | `updateReportBtn` | Update Report **(hidden)** | `updateReportWithPgn` |
| 1626 | `reportAppendVariantBtn` | Report Append Variant **(hidden)** | `function @14699` |
| 1941 | `toggleReportLoaderBtn` | ▶ Report Loader | `getElementById` |
| 1947 | `parseReportBtn` | Parse Report | `parseAnalysisReport` |
| 1951 | `loadReportSectionBtn` | Load Selected | `loadReportSection` |
| 1952 | `loadHighlightedBtn` | Load Highlighted Text | `loadHighlightedText` |
| 2112 | `closeReportFilesModal` | Close | `function @14635` |
| 12390 | `—` | Load *(~inherited)* | `—` |

## Notes

- 39 buttons — the largest family, and the oldest. Several ship hidden (`display:none`): `loadPgnFromHighlight` (1035), `loadFenVariantFromHighlight` (1036), `loadPreloadedReports` (1178), `viewPreloadedReports` (1180), `prevVariant` (1596), `nextVariant` (1597).
- A button that is `display:none` and still has a handler bound is the clearest definition of clutter in this repo. Start here: six buttons, zero UI risk.
- `react-chat-report-viewer/` (107 tracked files) and `preloaded_reports/` (23) are not loaded by index.html at all — they are in your `vercel.json` excludeFiles list, which is the tell.
- Careful: `board2` IS the main board (`board2PrevMove`/`board2NextMove` are the real Prev/Next). The *report* half goes; the *board* half stays.
