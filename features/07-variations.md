# Variation adders (all of them)

**Verdict: CUT — keep 2 of 8**

Eight routes to the same outcome: attach a line to a move in the PGN.

**Entry point.** `Add Var.` (1577) · `Add Var. 2` (1499) · `1-Line` (1502) · `Play Out` (1500) · `Insert as Variation` (1241 and 1464) · `Fill Variations` (1206) · `Add to PGN` (1216) · `Build new PGN` from Lichess Links (1663).

**Footprint.** 34 buttons · 241 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**localStorage.** `lichessAnchorPath` · `lichessPlayoutText`

**Other files.** `stockfish_add_variation.py` · `hidden-features/extend-variation-lichess.html`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1194 | `analyze-variation-btn` | Analyze (Tab) | `analyzeForVariation` |
| 1205 | `fill-variations-btn` | Fill Variations | `fillMissingVariations` |
| 1215 | `add-variation-btn` | Add to PGN | `addVariationToPgn` |
| 1219 | `—` | Hide | `clearVariationResult` |
| 1240 | `insert-variation-btn` | Insert as Variation | `insertPastedVariation` |
| 1244 | `—` | 📋 Paste from Clipboard | `readText, then, getElementById` |
| 1248 | `—` | Clear | `getElementById, resetDragBuild` |
| 1463 | `—` | Insert as Variation | `getElementById, getElementById, insertPastedVariation, getElementById` |
| 1467 | `—` | Paste from Clipboard | `readText, then, getElementById` |
| 1471 | `—` | Clear | `getElementById` |
| 1490 | `cycleVarBtn` | Cycle Var. | `cycleVariationStepOut @12831` |
| 1491 | `—` | ↑ Up Out | `exitVariationToBranchMainLineMove, showToast` |
| 1499 | `playout-btn` | Play Out | `playOutToEnd` |
| 1501 | `oneline-btn` | 1-Line | `openOneLineModal` |
| 1576 | `analyze-variation-btn2` | Add Var. | `analyzeForVariation` |
| 1579 | `clearVariationsBtn` | Clear Var. | `function @13556` |
| 1643 | `—` | ✕ | `getElementById` |
| 1652 | `—` | Copy White to Move | `copyLichessFromPos` |
| 1653 | `—` | Copy Black to Move | `copyLichessFromPos` |
| 1662 | `—` | Build new PGN (adds line + copies full PGN) | `buildLichessPlayout` |
| 1670 | `—` | Copy White Analysis URL | `writeText, getElementById` |
| 1677 | `—` | Copy Black Analysis URL | `writeText, getElementById` |
| 1685 | `—` | Copy Editor URL | `writeText, getElementById` |
| 1703 | `—` | ✕ | `closeAddVar2` |
| 1709 | `addVar2Go` | Add as variation | `commitAddVar2` |
| 1763 | `—` | ✕ | `getElementById` |
| 1768 | `oneLinePasteBtn` | Paste & Copy | `oneLinePaste` |
| 1769 | `oneLineTagBtn` | Remove Tags: OFF | `oneLineToggleTags` |
| 1772 | `oneLineCopyBtn` | Copy single line | `oneLineCopy` |
| 1844 | `—` | ✕ | `getElementById` |
| 1852 | `playoutModalHereBtn` | — | `playoutModalChoose` |
| 1853 | `playoutModalPrevBtn` | — | `playoutModalChoose` |
| 1854 | `—` | Cancel | `getElementById` |
| 1906 | `—` | Copy One-Line | `copyTextViewOneLine` |

## Notes

- You need exactly two intents: *the engine suggests a line* (`Add Var.` → `analyzeForVariation`/`addVariationToPgn`) and *I paste a line* (`Add Var. 2` → `commitAddVar2`).
- `Insert as Variation` exists twice, at index.html:1241 and index.html:1464, against two different textareas (`insert-variation-input` and `insert-variation-input2`). That alone is a free delete.
- `1-Line`, `Fill Variations`, `Play Out` and the Lichess `Build new PGN` all end in the same node-attach call by a longer road.
- Cut these last — they are the most entangled with the move tree, so do them one commit each with the inline-script check in between.
