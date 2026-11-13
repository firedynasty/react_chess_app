# Practice (play Stockfish from a move)

**Verdict: KEEP, trim its copy row**

Play the engine from the highlighted move, then copy the result as a From-Position snippet, flatten it, save to puzzles, or Load & Analyze it back.

**Entry point.** `Practice` (index.html:1501) → `#practiceModal` → `#practiceResultModal`.

**Footprint.** 15 buttons · 190 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**API.** `/api/puzzles`

**localStorage.** `practiceSaveCategory`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1359 | `—` | Snippet | `practiceShowResult` |
| 1360 | `—` | Back to game | `practiceBack` |
| 1498 | `addVar2Btn` | Add Var. 2 | `openAddVar2` |
| 1500 | `practice-btn` | Practice | `openPracticeModal` |
| 1503 | `loadAnalyzeMini` | Load & Analyze | `loadAndAnalyze` |
| 1724 | `—` | ✕ | `getElementById` |
| 1734 | `—` | Start practice | `practiceStart` |
| 1735 | `—` | Cancel | `getElementById` |
| 1779 | `—` | ✕ | `getElementById` |
| 1784 | `practiceCopyBtn` | Copy snippet | `practiceCopy` |
| 1785 | `practiceFlattenBtn` | Flatten | `practiceToggleFlatten` |
| 1793 | `practiceOneLineCopyBtn` | Copy line | `practiceCopyOneLine` |
| 1797 | `—` | Keep playing | `getElementById` |
| 1798 | `—` | Back to game | `practiceBack` |
| 1809 | `practiceSaveBtn` | Save to puzzles | `practiceSave` |

## Notes

- Keep the feature — it is the one place the app makes you *do* something rather than read.
- `Copy snippet` / `Flatten` / `Copy line` (index.html:1785-1794) duplicate `lnCopyVarResult` / `lnShowVarFlatten` / `lnCopyVarOneLine`. Same text, same shape, different functions.
- `Save to puzzles` (1810) duplicates `pzSave` (1836).
