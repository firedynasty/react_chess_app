# Contract: "Download PGN" Button → `downloadPgn()`

This app has no external API; its "interface" is the in-page contract between the toolbar button and the function it triggers, plus how that function reuses the existing PGN-resolution and download-file mechanics already present in `index.html`, and how it layers eval tags on top via a new `moveTreeToPgnWithEvals()`.

## UI contract: button

| Aspect | Contract |
|---|---|
| Element | New `<button id="downloadPgnBtn">`, placed immediately after `#copyPgnBtn` in the toolbar (`index.html:1204`) |
| Label | "Download PGN" |
| Trigger | `onclick="downloadPgn()"` |
| Enabled state | Always clickable (no disabled state) — matches `#copyPgnBtn`'s own always-enabled pattern; the "nothing to download" case is handled inside `downloadPgn()` itself (see below), not via a disabled attribute |

## Function contract: `downloadPgn()`

- **Input**: none (reads global state, mirroring `copyPgnToClipboard()`'s own signature).
- **Behavior**:
  1. Resolve PGN text: `window.moveTree ? moveTreeToPgnWithEvals(window.moveTree) : (window.currentLoadedPgn || window.annotatedPgnWithVariations)`. (Only the tree branch differs from `copyPgnToClipboard()` — the fallback branch is identical and carries no eval tags, per spec Assumptions.)
  2. If the resolved text is falsy/empty, surface a warning to the user (matching `copyPgnToClipboard()`'s `log('No PGN available to copy', 'warning')` pattern, e.g. `log('No PGN available to download', 'warning')`) and return without creating a download (FR-005).
  3. Build a `Blob` from the PGN text.
  4. Compute a timestamped filename per `data-model.md` ("Download Filename").
  5. Create a throwaway `<a>` element, set `href` to `URL.createObjectURL(blob)` and `download` to the computed filename, call `.click()`, then `URL.revokeObjectURL(...)` to release the object URL (mirrors `fenQueueDownload()`, `index.html:8795-8814`).
  6. Log a success message (matching the app's existing `log(..., 'success')` convention used by `copyPgnToClipboard()`).
- **Output**: none (side effect: browser initiates a file save/download).
- **Errors**: No PGN available → warning log, no-op (see step 2). No other error paths — `Blob`/`URL.createObjectURL`/anchor `download` are relied on elsewhere in this file without additional error handling, so this feature follows the same assumption of browser support.

## Function contract: `moveTreeToPgnWithEvals(rootNode)`

- **Input**: `rootNode` — same Move Node tree shape `moveTreeToPgn()` already traverses (`001-move-tree-context-menu/data-model.md`).
- **Behavior**: Identical traversal/serialization to `moveTreeToPgn()` (same move-number formatting, same mainline-then-variations ordering), with one addition at the point each node's comment is written: if `window.positionEvalMap[node.fen] !== undefined`, format that value per `data-model.md` ("Value: Eval Tag") and append it to the node's comment text (space-separated if a user comment already exists) before it is wrapped in `{...}`.
- **Output**: PGN move-text string, same format `moveTreeToPgn()` returns, with eval tags interleaved.
- **Non-effect**: Read-only with respect to `window.positionEvalMap` and every `node` — no field on any Move Node is mutated; the eval text exists only in the returned string.
- **Errors**: none — a missing `positionEvalMap` entry for a given node is the expected common case (FR-008), not a failure.

## Non-effects

- MUST NOT alter `window.moveTree` (including any node's `comment`/`annotation`), `window.currentLoadedPgn`, `window.annotatedPgnWithVariations`, or `window.positionEvalMap`.
- MUST NOT alter `copyPgnToClipboard()`'s behavior, `moveTreeToPgn()`'s behavior, its button (`#copyPgnBtn`), or the clipboard (FR-006).
- MUST NOT trigger new engine analysis or otherwise call into the "Get Eval" analysis path (FR-009) — only reads whatever is already in `positionEvalMap`.
- MUST NOT make a network request — the entire operation is client-side, consistent with the rest of this static app.

## Downstream contract (unchanged, verified compatible)

- `moveTreeToPgn(window.moveTree)` (`index.html:3162`): untouched; `copyPgnToClipboard()` keeps using it exactly as before.
- `copyPgnToClipboard()` (`index.html:3214`): untouched; continues to own clipboard export independently of the new download path.
- `window.positionEvalMap` (populated by `getEvalForLoadedPgn()`, `index.html:7198-7264`, and other existing eval-fetch call sites): read-only consumer added; no existing writer of this map changes.
