# Duplicate controls

**Verdict: CUT — free, and it is the clutter you actually see.**

Two control rows do the same job. The mini quick-access bar (`index.html:1485-1529`) was built
on top of the original row below the board (`index.html:1564-1627`), but the original was never
removed. `index.html:1170` says so out loud:

> `<!-- Hidden (not removed): JS still binds to these button IDs. Replace with supabase_fens_pgns content later. -->`

Nothing here is a feature decision. It is the same feature, wired twice.

**Done so far.** `#loadToBoard` (the **load to board** pair) is culled — see
[01-core-board.md](01-core-board.md) `## Culled` — and all 11 Dropbox buttons went with the
feature ([15-dropbox.md](15-dropbox.md)), which also took three of the five hidden-but-revealed
ones. Line numbers below are pre-cull; work from the ids.

## 11 buttons whose only job is clicking another button

Pure indirection. Move the real handler onto the visible button, delete the target.

| line | label | clicks |
|---:|---|---|
| 1176 | 📂 Select Reports Folder | `#reportFolderInput` |
| 1489 | ← Prev | `#board2PrevMove` |
| 1490 | Next → | `#board2NextMove` |
| 1508 | Export FEN | `#exportFenBtn` |
| 1516 | Flip Board | `#flip_board2` |
| 1517 | Lichess Links | `#lichessLinksBtn` |
| 1519 | Reanalyze | `#analyzeGameBtn` |
| 1520 | Get Eval | `#getEvalBtn` |
| 2090 | ⬆ Load JSON | `#plJsonInput` |
| 2091 | 📁 Load folder | `#plFolderInput` |
| 18970 | ⬆ Load JSON (replaces) | `#ppLoadFile` |

Four of these — `#reportFolderInput`, `#plJsonInput`, `#plFolderInput`, `#ppLoadFile` — target a
hidden `<input type="file">`, not a button. That is the standard way to style a file picker, so
those stay. The other **seven** (lines 1489, 1490, 1508, 1516, 1517, 1519, 1520) are a visible
button clicking a second visible button in the row below it. Those are the free deletes.

## 10 buttons shipped with `display:none`

Hidden in the markup, still in the DOM, still with a click handler bound. **But hidden is not the
same as dead** — two of these are revealed by JS when their feature becomes available, so check
before deleting:

| id | revealed at | why |
|---|---|---|
| `viewPreloadedReports` | `index.html:14468`, `14519` | appears once reports load |
| `appendByOpeningBtn` | `index.html:14601` | appears once reports load |

The three Dropbox ones that used to head this table — `dbFilesBtn`, `dbLogoutBtn`, `dbSaveBtn`,
revealed by `updateDropboxButtons()` after sign-in — are gone with the feature
([15-dropbox.md](15-dropbox.md)).

**The other eight are never revealed by anything.** No `style.display` assignment anywhere in the
file sets them visible. They are dead UI with live handlers attached:

| line | id | label | only other reference |
|---:|---|---|---|
| 862 | `analyzeFenBtn` | Analyze Position | enabled/disabled at 3373, 4300, 4345 — never shown |
| 1035 | `loadPgnFromHighlight` | Load PGN from Highlight | handler bound at 15403 |
| 1036 | `loadFenVariantFromHighlight` | Load [Fen Variant] from Highlight | handler bound at 15444 |
| 1178 | `loadPreloadedReports` | 📋 Preloaded Reports | handler bound at 14485, fetches `preloaded/reports.json` |
| 1596 | `prevVariant` | ← Prev FEN/PGN | handler bound at 14250 |
| 1597 | `nextVariant` | Next FEN/PGN → | handler bound at 14267 |
| 1607 | `updateReportBtn` | Update Report | 4648 flashes "Updated!" onto an invisible button |
| 1627 | `reportAppendVariantBtn` | Report Append Variant | handler bound at 14740 |

Six of the eight belong to [17-study-tool-report.md](17-study-tool-report.md), which is the
independent reason to start there. Deleting these eight changes nothing on screen.

## All 10, as found

| line | id | label | handler |
|---:|---|---|---|
| 862 | `analyzeFenBtn` | Analyze Position | `analyzeFen` |
| 1035 | `loadPgnFromHighlight` | Load PGN from Highlight | `function @15403` |
| 1036 | `loadFenVariantFromHighlight` | Load [Fen Variant] from Highlight | `function @15444` |
| 1178 | `loadPreloadedReports` | 📋 Preloaded Reports | `async @14485` |
| 1180 | `viewPreloadedReports` | 📋 View Reports | `openReportFilesModal @14543` |
| 1184 | `appendByOpeningBtn` | 📚 Append Opening Reports | `async @14608` |
| 1596 | `prevVariant` | ← Prev FEN/PGN | `function @14250` |
| 1597 | `nextVariant` | Next FEN/PGN → | `function @14267` |
| 1607 | `updateReportBtn` | Update Report | `updateReportWithPgn` |
| 1627 | `reportAppendVariantBtn` | Report Append Variant | `function @14740` |

## 31 labels appearing on more than one button

`Clear`, `Close`, `Cancel`, `Save`, `Load` repeat because each modal has its own — that is fine.
The ones to act on are marked **identical handler**: two buttons, one function, no reason.

The **save** and **search** pairs dropped off this list when Dropbox went: `#dropboxSaveConfirmBtn`
and `#dropboxSearchBtn` were the second half of each, so `#-` → `saveMoveComment` and
`#gdrive-picker-search-btn` are now the only buttons with those labels.


**clear** — 10 buttons

- `index.html:868` `#-` → `clearResults` · [core-board](01-core-board.md)
- `index.html:916` `#sbClearReportBtn` → `sbClearReportList` · [supabase-games](03-supabase-games.md)
- `index.html:1064` `#-` → `getElementById` · [study-tool-report](17-study-tool-report.md)
- `index.html:1101` `#-` → `lnXferClear` · [puzzles-transfer](05-puzzles-transfer.md)
- `index.html:1249` `#-` → `getElementById, resetDragBuild` · [variations](07-variations.md)
- `index.html:1276` `#-` → `getElementById` · [move-comment](11-move-comment.md)
- `index.html:1296` `#-` → `getElementById, getElementById, focus` · [move-comment](11-move-comment.md)
- `index.html:1472` `#-` → `getElementById` · [variations](07-variations.md)
- `index.html:1753` `#-` → `coachPgnClear` · [coach-ai](16-coach-ai.md)
- `index.html:1972` `#-` → `gdriveClear` · [sheets-drive](14-sheets-drive.md)

**cancel** — 4 buttons

- `index.html:1736` `#-` → `getElementById` · [practice](08-practice.md)
- `index.html:1855` `#-` → `getElementById` · [variations](07-variations.md)
- `index.html:1933` `#-` → `getElementById` · [fen-export](18-fen-export.md)
- `index.html:18922` `#-` → `ppCloseAdd` · [print-cards](12-print-cards.md)

**close** — 4 buttons

- `index.html:1164` `#-` → `getElementById` · [supabase-lines](04-supabase-lines.md)
- `index.html:1559` `#-` → `getElementById` · [supabase-lines](04-supabase-lines.md)
- `index.html:2113` `#closeReportFilesModal` → `function @14676` · [study-tool-report](17-study-tool-report.md)
- `index.html:19228` `#-` → `getElementById` · [print-cards](12-print-cards.md)

**copy pgn** — 3 buttons

- `index.html:1521` `#copyBoardPgnBtnMini` → `copyPgnToClipboard` · [core-board](01-core-board.md)
- `index.html:1605` `#copyBoardPgnBtn` → `copyPgnToClipboard` · [core-board](01-core-board.md)
- `index.html:1757` `#coachPgnCopyBtn` → `coachPgnCopy` · [coach-ai](16-coach-ai.md)

**copy snippet** — 3 buttons

- `index.html:1539` `#copyVarResultCopyBtn` → `lnCopyVarResult` · [supabase-lines](04-supabase-lines.md)
- `index.html:1785` `#practiceCopyBtn` → `practiceCopy` · [practice](08-practice.md)
- `index.html:20495` `#-` → `mmCopySnippet` · [what-went-wrong](09-what-went-wrong.md)

**load** — 3 buttons

- `index.html:1128` `#-` → `lnLoadRowByRef` · [supabase-lines](04-supabase-lines.md)
- `index.html:1934` `#-` → `submitLoadFenModal` · [fen-export](18-fen-export.md)
- `index.html:12391` `#-` → `—` · [study-tool-report](17-study-tool-report.md)

**📋 paste from clipboard** — 3 buttons  — **identical handler**

- `index.html:1060` `#-` → `readText, then, getElementById` · [study-tool-report](17-study-tool-report.md)
- `index.html:1245` `#-` → `readText, then, getElementById` · [variations](07-variations.md)
- `index.html:1272` `#-` → `readText, then, getElementById` · [move-comment](11-move-comment.md)

**analyze game** — 2 buttons

- `index.html:861` `#analyzeBtn` → `analyzeGame` · [core-board](01-core-board.md)
- `index.html:1584` `#analyzeGameBtn` → `analyzeLoadedGame` · [study-tool-report](17-study-tool-report.md)

**back to game** — 2 buttons  — **identical handler**

- `index.html:1361` `#-` → `practiceBack` · [practice](08-practice.md)
- `index.html:1799` `#-` → `practiceBack` · [practice](08-practice.md)

**copy** — 2 buttons

- `index.html:1603` `#gdriveRowCopyBtn` → `function @17749` · [sheets-drive](14-sheets-drive.md)
- `index.html:1971` `#-` → `gdriveCopyAll` · [sheets-drive](14-sheets-drive.md)

**copy line** — 2 buttons

- `index.html:1545` `#copyVarOneLineCopyBtn` → `lnCopyVarOneLine` · [supabase-lines](04-supabase-lines.md)
- `index.html:1794` `#practiceOneLineCopyBtn` → `practiceCopyOneLine` · [practice](08-practice.md)

**export fen** — 2 buttons

- `index.html:1508` `#exportFenBtnMini` → `proxy → #exportFenBtn` · [fen-export](18-fen-export.md)
- `index.html:1610` `#exportFenBtn` → `function @13396` · [fen-export](18-fen-export.md)

**flatten** — 2 buttons

- `index.html:1540` `#copyVarFlattenBtn` → `lnShowVarFlatten` · [supabase-lines](04-supabase-lines.md)
- `index.html:1786` `#practiceFlattenBtn` → `practiceToggleFlatten` · [practice](08-practice.md)

**flip board** — 2 buttons

- `index.html:1516` `#-` → `proxy → #flip_board2` · [study-tool-report](17-study-tool-report.md)
- `index.html:1564` `#flip_board2` → `function @13571` · [study-tool-report](17-study-tool-report.md)

**get eval** — 2 buttons

- `index.html:1520` `#getEvalBtnMini` → `proxy → #getEvalBtn` · [study-tool-report](17-study-tool-report.md)
- `index.html:1585` `#getEvalBtn` → `getEvalForLoadedPgn @12843` · [study-tool-report](17-study-tool-report.md)

**hints** — 2 buttons  — **identical handler**

- `index.html:865` `#-` → `openHintsModal` · [core-board](01-core-board.md)
- `index.html:1529` `#-` → `openHintsModal` · [core-board](01-core-board.md)

**insert as variation** — 2 buttons

- `index.html:1241` `#insert-variation-btn` → `insertPastedVariation` · [variations](07-variations.md)
- `index.html:1464` `#-` → `getElementById, getElementById, insertPastedVariation, getElementById` · [variations](07-variations.md)

**lichess links** — 2 buttons

- `index.html:1517` `#-` → `proxy → #lichessLinksBtn` · [core-board](01-core-board.md)
- `index.html:1611` `#lichessLinksBtn` → `function @13455` · [core-board](01-core-board.md)

**load selected** — 2 buttons

- `index.html:904` `#sbLoadGameBtn` → `sbLoadSelectedGame` · [supabase-games](03-supabase-games.md)
- `index.html:1952` `#loadReportSectionBtn` → `loadReportSection` · [study-tool-report](17-study-tool-report.md)

**next →** — 2 buttons

- `index.html:1490` `#-` → `proxy → #board2NextMove` · [study-tool-report](17-study-tool-report.md)
- `index.html:1571` `#board2NextMove` → `board2NextMove @12819` · [study-tool-report](17-study-tool-report.md)

**next ▶** — 2 buttons

- `index.html:1525` `#nextVarBtnMini` → `lnGridNext` · [supabase-lines](04-supabase-lines.md)
- `index.html:2099` `#-` → `plStep` · [pgn-library](13-pgn-library.md)

**save to puzzles** — 2 buttons

- `index.html:1810` `#practiceSaveBtn` → `practiceSave` · [practice](08-practice.md)
- `index.html:1836` `#pzSaveBtn` → `pzSave` · [puzzles-save](06-puzzles-save.md)

**signals on** — 2 buttons  — **identical handler**

- `index.html:1513` `#toggleBorderBtnMini` → `toggleBoardBorder` · [core-board](01-core-board.md)
- `index.html:1614` `#toggleBorderBtn` → `toggleBoardBorder` · [core-board](01-core-board.md)

**sound on** — 2 buttons  — **identical handler**

- `index.html:1512` `#toggleSoundBtnMini` → `toggleChessSound` · [core-board](01-core-board.md)
- `index.html:1613` `#toggleSoundBtn` → `toggleChessSound` · [core-board](01-core-board.md)

**← prev** — 2 buttons

- `index.html:1489` `#-` → `proxy → #board2PrevMove` · [study-tool-report](17-study-tool-report.md)
- `index.html:1569` `#board2PrevMove` → `board2PrevMove @12824` · [study-tool-report](17-study-tool-report.md)

**⬇ export json** — 2 buttons

- `index.html:2092` `#-` → `plExportJson` · [pgn-library](13-pgn-library.md)
- `index.html:18969` `#-` → `ppExportJson` · [print-cards](12-print-cards.md)

**💬 coach chat** — 2 buttons  — **identical handler**

- `index.html:1515` `#-` → `openChessCoachChatModal` · [coach-ai](16-coach-ai.md)
- `index.html:1566` `#-` → `openChessCoachChatModal` · [coach-ai](16-coach-ai.md)

**📊 view** — 2 buttons  — **identical handler**

- `index.html:1129` `#-` → `lnGridOpen` · [supabase-lines](04-supabase-lines.md)
- `index.html:1524` `#viewVarBtnMini` → `lnGridOpen` · [supabase-lines](04-supabase-lines.md)

**📋 copy url** — 2 buttons  — **identical handler**

- `index.html:926` `#sbCopyGameLinkBtn` → `sbCopyGameLink` · [supabase-games](03-supabase-games.md)
- `index.html:1527` `#copyGameLinkBtnMini` → `sbCopyGameLink` · [supabase-games](03-supabase-games.md)

**📥 fetch games** — 2 buttons

- `index.html:785` `#fetch-games-btn` → `fetchChesscomGames` · [game-sources](02-game-sources.md)
- `index.html:805` `#fetch-lichess-btn` → `fetchLichessGames` · [game-sources](02-game-sources.md)

**🖨 print** — 2 buttons

- `index.html:18945` `#-` → `ppLinePrint` · [print-cards](12-print-cards.md)
- `index.html:18965` `#-` → `ppPrint` · [print-cards](12-print-cards.md)
