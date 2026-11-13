# Clipboard sprawl

**Verdict: COLLAPSE to three functions.**

`index.html` has **27 `clipboard.writeText` calls** and **14 `clipboard.readText` calls**, behind **35 buttons**. They move three shapes of thing:

1. **a FEN** — `copyExportedFen`, `mmCopyFen`, `gdriveCopyCell`, the three `fenLichessModal` URL buttons
2. **a From-Position snippet** — `lnCopyVarResult`, `practiceCopy`, `mmCopySnippet`, and the
   `lnShowVarFlatten` / `practiceToggleFlatten` pair
3. **a PGN or a one-line move list** — `copyPgnToClipboard`, `coachPgnCopy`, `lnCopyVarOneLine`,
   `practiceCopyOneLine`, `copyTextViewOneLine`, `copyTextViewFormatted`, `oneLineCopy`,
   `copyEvalsForPaste`, `lnCopyMoveInfo`, `mmCopy`, `mmNote`, `lnXferCopy`, `gdriveCopyAll`

Four of them copy a one-line move list: `copyTextViewOneLine` (20-text-view),
`oneLineCopy` (07-variations), `lnCopyVarOneLine` (04-supabase-lines) and
`practiceCopyOneLine` (08-practice). Same output, four implementations.

Write `copyFen(fen)`, `copySnippet(node)` and `copyPgn(pgn, {oneLine})` once, with one toast,
and point every button at them. This cannot break the move tree, so it is the safest
substantial cut available — and it removes the most felt clutter per line changed.

The three `📋 Paste from Clipboard` buttons (`index.html:1060`, `1245`, `1272`) and the
fourth at `1468` are the same story on the read side.

**Done so far.** Four of these went with the Supabase game library
([03-supabase-games.md](03-supabase-games.md)) rather than with this cut: `#sbCopyGameLinkBtn`,
`#sbCopySectionBtn`, the report modal's `Copy All`, and the mini bar's `#copyGameLinkBtnMini`.
That is two `writeText` calls and the only two copies that produced a URL rather than a FEN,
a snippet or a PGN — so the three-function collapse below now covers every remaining copy button.

## All 35 copy buttons

| line | id | label | handler | feature |
|---:|---|---|---|---|
| 1037 | `copyReportText` | Copy Text | `function @15481` | [study-tool-report](17-study-tool-report.md) |
| 1100 | `—` | 📋 Copy all rows | `lnXferCopy` | [puzzles-transfer](05-puzzles-transfer.md) |
| 1413 | `—` | Copy + Lichess Editor | `copyTypedStatusAndOpenEditor` | [typed-move](19-typed-move.md) |
| 1417 | `—` | 📋 Copy | `writeText, getElementById` | [typed-move](19-typed-move.md) |
| 1521 | `copyBoardPgnBtnMini` | Copy PGN | `copyPgnToClipboard` | [core-board](01-core-board.md) |
| 1522 | `copyMoveInfoBtnMini` | Copy Move Info | `lnCopyMoveInfo` | [supabase-lines](04-supabase-lines.md) |
| 1523 | `copyVarBtnMini` | Copy Var | `lnOpenVarSnippetModal` | [supabase-lines](04-supabase-lines.md) |
| 1539 | `copyVarResultCopyBtn` | Copy snippet | `lnCopyVarResult` | [supabase-lines](04-supabase-lines.md) |
| 1540 | `copyVarFlattenBtn` | Flatten | `lnShowVarFlatten` | [supabase-lines](04-supabase-lines.md) |
| 1545 | `copyVarOneLineCopyBtn` | Copy line | `lnCopyVarOneLine` | [supabase-lines](04-supabase-lines.md) |
| 1556 | `copyVarSaveBtn` | Append to chess_variations | `lnSaveVarToSupabase` | [supabase-lines](04-supabase-lines.md) |
| 1586 | `copyEvalsBtn` | 📋 Copy Evals | `copyEvalsForPaste` | [study-tool-report](17-study-tool-report.md) |
| 1603 | `gdriveRowCopyBtn` | Copy | `function @17749` | [sheets-drive](14-sheets-drive.md) |
| 1605 | `copyBoardPgnBtn` | Copy PGN | `copyPgnToClipboard` | [core-board](01-core-board.md) |
| 1653 | `—` | Copy White to Move | `copyLichessFromPos` | [variations](07-variations.md) |
| 1654 | `—` | Copy Black to Move | `copyLichessFromPos` | [variations](07-variations.md) |
| 1671 | `—` | Copy White Analysis URL | `writeText, getElementById` | [variations](07-variations.md) |
| 1678 | `—` | Copy Black Analysis URL | `writeText, getElementById` | [variations](07-variations.md) |
| 1686 | `—` | Copy Editor URL | `writeText, getElementById` | [variations](07-variations.md) |
| 1757 | `coachPgnCopyBtn` | Copy PGN | `coachPgnCopy` | [coach-ai](16-coach-ai.md) |
| 1769 | `oneLinePasteBtn` | Paste & Copy | `oneLinePaste` | [variations](07-variations.md) |
| 1773 | `oneLineCopyBtn` | Copy single line | `oneLineCopy` | [variations](07-variations.md) |
| 1785 | `practiceCopyBtn` | Copy snippet | `practiceCopy` | [practice](08-practice.md) |
| 1794 | `practiceOneLineCopyBtn` | Copy line | `practiceCopyOneLine` | [practice](08-practice.md) |
| 1870 | `—` | Copy White FEN | `copyExportedFen` | [fen-export](18-fen-export.md) |
| 1878 | `—` | Copy Black FEN | `copyExportedFen` | [fen-export](18-fen-export.md) |
| 1906 | `—` | Copy Formatted | `copyTextViewFormatted` | [text-view](20-text-view.md) |
| 1907 | `—` | Copy One-Line | `copyTextViewOneLine` | [variations](07-variations.md) |
| 1971 | `—` | Copy | `gdriveCopyAll` | [sheets-drive](14-sheets-drive.md) |
| 6022 | `—` | \ud83d\udccb | `stopPropagation, lnGridCopy` | [supabase-lines](04-supabase-lines.md) |
| 16904 | `—` | Copy Chat | `—` | [coach-ai](16-coach-ai.md) |
| 19858 | `—` | Copy all notes | `mmCopy` | [what-went-wrong](09-what-went-wrong.md) |
| 20494 | `—` | Copy this FEN | `mmCopyFen` | [what-went-wrong](09-what-went-wrong.md) |
| 20495 | `—` | Copy snippet | `mmCopySnippet` | [what-went-wrong](09-what-went-wrong.md) |
| 20647 | `—` | Copy notes | `mmNote` | [what-went-wrong](09-what-went-wrong.md) |

## Every `clipboard.writeText` call site

`1417`, `1671`, `1678`, `1686`, `2736`, `2746`, `4548`, `5708`, `6399`, `6860`, `6867`, `10461`, `11661`, `13315`, `13430`, `13558`, `15491`, `15756`, `16557`, `16652`, `17452`, `17632`, `17773`, `17784`, `17803`, `18034`, `18387`, `18496`, `18518`, `18531`, `20800`
