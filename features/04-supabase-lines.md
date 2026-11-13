# Supabase Lines pane (chess_* tables)

**Verdict: KEEP**

The ☰ side pane: save the board PGN as a named line, load by row # or name, browse rows in a grid, and append a variation to `chess_variations`.

**Entry point.** `☰` (index.html:990) opens `#supabase_fens_pgns`; `Copy Var` (index.html:1393) opens the snippet modal with `Append to chess_variations`.

**Footprint.** 20 buttons · 332 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**API.** `/api/lines`

**localStorage.** `lnPaneOpen`

**Other files.** `api/lines.js` · `chess-rag/sql/chess_variations.sql`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 990 | `lnPaneBtn` | ☰ | `lnPaneToggle` |
| 994 | `—` | ✕ | `lnPaneToggle` |
| 1025 | `—` | 💾 Save board PGN | `lnSaveLine` |
| 1032 | `—` | Load | `lnLoadRowByRef` |
| 1033 | `—` | 📊 View | `lnGridOpen` |
| 1034 | `—` | ↻ | `lnLoadRows` |
| 1043 | `—` | ✕ | `getElementById` |
| 1050 | `—` | ↻ | `lnGridOpen` |
| 1067 | `—` | Close | `getElementById` |
| 1393 | `copyVarBtnMini` | Copy Var | `lnOpenVarSnippetModal` |
| 1394 | `viewVarBtnMini` | 📊 View | `lnGridOpen` |
| 1424 | `copyMoveInfoBtnMini` | Copy Move Info | `lnCopyMoveInfo` |
| 1425 | `nextVarBtnMini` | Next ▶ | `lnGridNext` |
| 1438 | `copyVarResultCopyBtn` | Copy snippet | `lnCopyVarResult` |
| 1439 | `copyVarFlattenBtn` | Flatten | `lnShowVarFlatten` |
| 1444 | `copyVarOneLineCopyBtn` | Copy line | `lnCopyVarOneLine` |
| 1451 | `copyVarSaveBtn` | Append to chess_variations | `lnSaveVarToSupabase` |
| 1454 | `—` | Close *(~inherited)* | `getElementById` |
| 5298 | `—` | 📋 | `stopPropagation, lnGridCopy` |
| 5299 | `—` | 🗑 | `stopPropagation, lnGridDelete` |

## Notes

- Your three most recent commits built on this. It is the live half of the Supabase integration — keep it.
- Shares `api/lines.js` with the vercel_fen_saver repo (same file in both). Do not edit it one-sided.
- `Copy snippet` / `Flatten` / `Copy line` here (index.html:1439-1445) are byte-for-byte siblings of the Practice modal's three. See `clipboard-sprawl.md`.
- The line numbers above had also gone stale by ~98 when [03](03-supabase-games.md) was removed; they are refreshed from the current `BUTTONS.md`.
- **`Copy Var` and `📊 View` sit before `Sheets ▾`** in the `#miniNavControls` row (moved there from
  after `Copy Move Info`), so the two chess_variations controls lead that row's second half.
  `Copy Move Info` (1424) and `Next ▶` (1425) stayed put, so `Next ▶` — which steps through the
  grid's current order and filter — is no longer next to the `📊 View` that fills it.

## Culled

- **The second save box — `copyVarSaveNote` "variation", and `copyVarSaveCat`'s category role** —
  the snippet modal's `Save to Supabase` block now has **one** input, `copyVarSaveName`, holding
  the row's `name` verbatim. `chess_variations` has two columns (`name`, `pgn`), and three of its
  five rows (`stonewall_attack_the_knight`, `sampleagain_nextagain`, `blunder_piece`) never used
  the `category: variation` convention the two boxes existed to build.
  **Went with it:** `#copyVarNamePreview` and `lnVarNamePreview()` — with one box the preview only
  echoed the box — `lnJoinName()`, whose two callers were that preview and the save, and the
  two-input flex wrapper. 12 lines of `index.html` net.
  **Kept:** `LN_SEP`, and a name typed with a colon still matches vercel_fen_saver's `SB_SEP`
  shape. `lnSplitName()` survived this cut and went with the next one.
  **Changed with it:** the datalist suggests whole existing names instead of the part before the
  colon (`copyVarCatList` → `copyVarNameList`, `lnVarCats` / `lnVarLoadCategories` →
  `lnVarNames` / `lnVarLoadNames`), and `lnVarResetName()` replaces "clear the note, keep the
  category" — after a save, and when the modal reopens, it trims the box back to the text up to
  the first `": "` when there is one and clears it otherwise.

- **The grid's `variation` column — `#lnGridTh_note` and its cell** — removed, and with it
  `lnSplitName()`, whose only caller was the row mapping in `lnGridFetch`. The remaining column is
  **`name`** (`#lnGridTh_category` → `#lnGridTh_name`, sorting on `name`), showing the cell as
  stored: dropping the column alone would have hidden half of `cheesecake: sample` and
  `sampleagain: whites_mistake`, since `category` only ever held the text before the colon.
  `lnGridRows` entries are now `{id, name, pgn, side, moves}`; the empty-state `colspan` went 6 → 5.
  The filter box was already searching `r.name` and `r.moves`, so it is untouched. `LN_SEP`
  survives as the trim point in `lnVarResetName()` and nothing else.

- **`lnTable()` out of the grid's table default** — `lnGridOpen()` and `lnGridFetch()` resolve
  `table || lnGridTableName || LN_VAR_TABLE`, so the mini bar's `📊 View` with no argument opens
  **`chess_variations`** instead of whatever `#lnTableSelect` in the pane happened to show, which
  is `chess_lines` (its first `<option>`). That is what `viewVarBtnMini`'s tooltip has always
  claimed — "chess_variations, or whichever table you last viewed" — and `lnGridTableName` still
  carries the "last viewed" half within a page load. `#lnGridTableSel`'s options are generated by
  `lnVarLoadNames`' sibling `lnGridLoadTableList()` from `/api/lines?action=tables` and its
  selection follows `lnGridTableName`, so it lands on `chess_variations` too.
  **Not changed:** `#lnTableSelect` itself still starts on `chess_lines` and still drives
  `💾 Save board PGN` / `Load` / `↻` in the pane.
