# Supabase Lines pane (chess_* tables)

**Verdict: KEEP**

The ☰ side pane: save the board PGN as a named line, load by row # or name, browse rows in a grid, and append a variation to `chess_variations` — either the one on the board or one pasted in from Lichess.

**Entry point.** `☰` (index.html:990) opens `#supabase_fens_pgns`; `Copy Var` (index.html:1393) opens the snippet modal on the board's variation and `Paste Var` (index.html:1394) opens the same modal with the box editable, both ending in `Append to chess_variations`.

**Footprint.** 22 buttons · 348 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

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
| 1394 | `pasteVarBtnMini` | Paste Var | `lnOpenVarPasteModal` |
| 1395 | `viewVarBtnMini` | 📊 View | `lnGridOpen` |
| 1426 | `copyMoveInfoBtnMini` | Copy Move Info | `lnCopyMoveInfo` |
| 1427 | `nextVarBtnMini` | Next ▶ | `lnGridNext` |
| 1440 | `copyVarResultCopyBtn` | Copy snippet | `lnCopyVarResult` |
| 1441 | `copyVarFlattenBtn` | Flatten | `lnShowVarFlatten` |
| 1442 | `copyVarPasteInBtn` | Paste in *(hidden until paste mode)* | `lnVarPasteIn` |
| 1447 | `copyVarOneLineCopyBtn` | Copy line | `lnCopyVarOneLine` |
| 1454 | `copyVarSaveBtn` | Append to chess_variations | `lnSaveVarToSupabase` |
| 1457 | `—` | Close *(~inherited)* | `getElementById` |
| 5362 | `—` | 📋 | `stopPropagation, lnGridCopy` |
| 5363 | `—` | 🗑 | `stopPropagation, lnGridDelete` |

## Notes

- Your three most recent commits built on this. It is the live half of the Supabase integration — keep it.
- Shares `api/lines.js` with the vercel_fen_saver repo (same file in both). Do not edit it one-sided.
- `Copy snippet` / `Flatten` / `Copy line` here (index.html:1439-1445) are byte-for-byte siblings of the Practice modal's three. See `clipboard-sprawl.md`.
- The line numbers above had also gone stale by ~98 when [03](03-supabase-games.md) was removed; they are refreshed from the current `BUTTONS.md`.
- `copyVarPasteInBtn` ships `display:none` and is **revealed by JS** — `lnVarSnippetMode(true)`
  shows it, `lnVarSnippetMode(false)` hides it again. It is trap #3 in
  [duplicate-controls.md](duplicate-controls.md), not a dead hidden button.
- **`Copy Var` and `📊 View` sit before `Sheets ▾`** in the `#miniNavControls` row (moved there from
  after `Copy Move Info`), so the two chess_variations controls lead that row's second half.
  `Copy Move Info` (1424) and `Next ▶` (1425) stayed put, so `Next ▶` — which steps through the
  grid's current order and filter — is no longer next to the `📊 View` that fills it.

## Added

- **`Paste Var` (`pasteVarBtnMini`, index.html:1394) — the snippet modal run backwards.** `Copy Var`
  takes the variation on the board *out* to Lichess; this takes a line built *at*
  lichess.org/analysis in. It opens `#copyVarResultModal`, the same modal, in a paste mode set by
  **`lnVarSnippetMode(paste)`**: `#copyVarResultText` loses its `readonly`, gains a purple border
  and a `[Variant "From Position"]` placeholder, `#copyVarPasteInBtn` appears, and the heading and
  hint change. `lnOpenVarSnippetModal()` now calls `lnVarSnippetMode(false)` to put all of that
  back, so `Copy Var` behaves exactly as before.
  **Flow:** paste the Lichess block → type a name → **Enter**. The name box's existing
  `onkeydown` already saves, so no new save path: it is `lnSaveVarToSupabase()`, flattening to one
  line into `pgn` with the box as `name`, the `": "` prefix still kept for the next row by
  `lnVarResetName()`, and `lnVarLoadNames()` still suggesting existing names.
  **New:** `lnOpenVarPasteModal()`, `lnVarSnippetMode()`, `lnVarPasteIn()`, all three exported on
  `window` (the trap in `db57b4e`), plus `#copyVarPasteInBtn`, and the save now refuses a snippet
  with no `[FEN "…"]` tag instead of storing a row that cannot load.
  **Deliberately not there: no clipboard read on open.** The first cut auto-called
  `navigator.clipboard.readText()` from `lnOpenVarPasteModal`, which raises Chrome's native
  *"see text and images you copied"* bubble; the page is inert behind that prompt, so the modal
  opened with a textarea that swallowed every keystroke and looked broken. The read now happens
  only on `Paste in`, and `#copyVarResultText` carries `onkeydown="event.stopPropagation()"` —
  the guard `#addVar2Text` already uses — so no document-level key handler can reach it either.
  The board-nav handler (index.html:12520) does bail on `TEXTAREA`, so it was never the culprit.

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
