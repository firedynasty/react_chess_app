# Supabase Lines pane (chess_* tables)

**Verdict: KEEP**

The ☰ side pane: save the board PGN as a named line, load by row # or name, browse rows in a grid, and append a variation to `chess_variations`.

**Entry point.** `☰` (index.html:1086) opens `#supabase_fens_pgns`; `Copy Var` (index.html:1523) opens the snippet modal with `Append to chess_variations`.

**Footprint.** 20 buttons · 342 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**API.** `/api/lines`

**localStorage.** `lnPaneOpen`

**Other files.** `api/lines.js` · `chess-rag/sql/chess_variations.sql`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1085 | `lnPaneBtn` | ☰ | `lnPaneToggle` |
| 1089 | `—` | ✕ | `lnPaneToggle` |
| 1120 | `—` | 💾 Save board PGN | `lnSaveLine` |
| 1127 | `—` | Load | `lnLoadRowByRef` |
| 1128 | `—` | 📊 View | `lnGridOpen` |
| 1129 | `—` | ↻ | `lnLoadRows` |
| 1138 | `—` | ✕ | `getElementById` |
| 1145 | `—` | ↻ | `lnGridOpen` |
| 1163 | `—` | Close | `getElementById` |
| 1521 | `copyMoveInfoBtnMini` | Copy Move Info | `lnCopyMoveInfo` |
| 1522 | `copyVarBtnMini` | Copy Var | `lnOpenVarSnippetModal` |
| 1523 | `viewVarBtnMini` | 📊 View | `lnGridOpen` |
| 1524 | `nextVarBtnMini` | Next ▶ | `lnGridNext` |
| 1538 | `copyVarResultCopyBtn` | Copy snippet | `lnCopyVarResult` |
| 1539 | `copyVarFlattenBtn` | Flatten | `lnShowVarFlatten` |
| 1544 | `copyVarOneLineCopyBtn` | Copy line | `lnCopyVarOneLine` |
| 1555 | `copyVarSaveBtn` | Append to chess_variations | `lnSaveVarToSupabase` |
| 1558 | `—` | Close *(~inherited)* | `getElementById` |
| 6021 | `—` | \ud83d\udccb | `stopPropagation, lnGridCopy` |
| 6022 | `—` | \ud83d\uddd1 | `stopPropagation, lnGridDelete` |

## Notes

- Your three most recent commits built on this. It is the live half of the Supabase integration — keep it.
- Shares `api/lines.js` with the vercel_fen_saver repo (same file in both). Do not edit it one-sided.
- `Copy snippet` / `Flatten` / `Copy line` here (index.html:1539-1545) are byte-for-byte siblings of the Practice modal's three. See `clipboard-sprawl.md`.
