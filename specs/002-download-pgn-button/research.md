# Phase 0 Research: Download PGN Button

No `[NEEDS CLARIFICATION]` markers remain in the Technical Context — all decisions below were resolved by reading the existing `index.html` implementation directly (see line references), since this feature is a small addition alongside an already-working export path.

## Decision: Reuse `copyPgnToClipboard()`'s exact PGN-resolution logic; do not add a second way to derive PGN text

- **Rationale**: `copyPgnToClipboard()` (`index.html:3214`) already encodes the app's one source of truth for "what is the current PGN": prefer `moveTreeToPgn(window.moveTree)` when a live tree exists (picks up in-session edits/annotations), else fall back to `window.currentLoadedPgn || window.annotatedPgnWithVariations`. Duplicating this logic independently for the download path would risk the two features silently diverging (e.g. one reflecting an edit the other doesn't) — exactly the kind of bug spec FR-002/FR-006 and SC-003 rule out.
- **Alternatives considered**:
  - *Re-derive PGN from the board/game object directly* — rejected: would bypass in-session tree edits (annotations, variations) that only live in `window.moveTree`, producing a downloaded file that doesn't match what "Copy PGN" would produce at the same moment.

## Decision: Use the existing `Blob` + `URL.createObjectURL` + anchor-`download` pattern already present in this file

- **Rationale**: `index.html` already implements client-side file downloads this exact way in two places — `fenQueueDownload()` (`index.html:8795-8814`, CSV) and the board-images ZIP export (`index.html:13107-13111`). Reusing the same pattern needs no new dependency, no server round-trip, and stays consistent with how "download a file" already works elsewhere in this app.
- **Alternatives considered**:
  - *`data:` URI on the anchor's `href`* — rejected: works but is the older, less-preferred approach; `Blob`/`createObjectURL` is what this codebase already standardized on and handles larger PGNs (with many variations/comments) more reliably.
  - *Server endpoint that returns the PGN as an attachment* — rejected: introduces a network round-trip and a new `api/*` route for a value that's already sitting in the browser's memory; violates the "no build step / no new backend" constraint the existing single-file app operates under.

## Decision: Timestamp-based filename for uniqueness (FR-004)

- **Rationale**: The existing `fenQueueDownload()` already derives its filename from `new Date().toISOString().slice(0,10)` (date only, `puzzles_2026-09-19.csv`). For PGN downloads, a user is more likely to click "Download PGN" multiple times in the same session (e.g. after each edit) than a CSV export, so date-only granularity could collide within a day. Using a full timestamp (date + time, colons replaced since `:` is invalid in Windows filenames) avoids same-day collisions while staying consistent with the existing naming convention (`prefix_timestamp.ext`).
- **Alternatives considered**:
  - *Date-only filename (mirroring `fenQueueDownload()` exactly)* — rejected: multiple downloads in one day would overwrite each other in the browser's default "replace on same name" behavior on some OS/browser combos, violating spec SC-002.
  - *Random ID/UUID suffix* — rejected: less human-readable than a timestamp and provides no information about when the file was generated; timestamp already satisfies the uniqueness requirement for this app's realistic usage pattern (see spec Assumptions: same-session, same-machine uniqueness only).

## Decision: Add a separate `moveTreeToPgnWithEvals()` rather than modifying `moveTreeToPgn()` in place

- **Rationale**: `moveTreeToPgn()` is also used by `copyPgnToClipboard()` (`index.html:3218`) and by other existing report-sync call sites (e.g. `index.html:4574`, `4821`, `6592`, `7958`). The user confirmed eval tags should apply only to the download, not to "Copy PGN" or any of those other consumers (spec FR-006). Branching inside `moveTreeToPgn()` on some flag would risk a future caller accidentally passing the wrong flag and silently changing behavior elsewhere; a separate function makes the scope explicit and keeps every existing call site provably unaffected.
- **Alternatives considered**:
  - *Add an `includeEvals` parameter to `moveTreeToPgn()`* — rejected: works but couples an eval-specific concern into a function several unrelated features already depend on, for a one-off consumer.
  - *Post-process the plain PGN string from `moveTreeToPgn()` to splice in eval comments* — rejected: would require re-deriving each move's FEN by replaying the PGN text (chess.js) just to look it back up in `positionEvalMap`, when the move tree already carries `node.fen` directly during traversal.

## Decision: Format eval tags using the same convention as `chess-rag/ingest.py`'s `_fmt_eval`

- **Rationale**: `window.positionEvalMap[fen]` already stores a White-POV score using the identical `mate_score=10000` encoding `ingest.py`'s `evaluate()`/`_fmt_eval()` use (confirmed at `index.html:2341-2343`: `scoreType === 'mate' ? (scoreValue > 0 ? 10000 - scoreValue : -10000 - scoreValue) : scoreValue`, vs. `ingest.py`'s `info["score"].white().score(mate_score=10000)`). Porting the same threshold (`abs(cp) >= 9900` → mate) and formatting (`#N` for mate, `cp/100` to two decimals otherwise) means downloaded files use PGN eval-comment syntax any tool already reading `ingest.py`'s output (e.g. `chess-rag/tree_viz`/`report.py`) can parse without a special case.
- **Alternatives considered**:
  - *Invent a simpler/different eval-tag format* — rejected: would create two incompatible `[%eval ...]` conventions across the codebase for no benefit, and risks breaking any downstream parser that expects `ingest.py`'s format.

## Decision: No automated test suite; validate manually per `quickstart.md`

- **Rationale**: Consistent with `001-move-tree-context-menu/research.md` — `index.html` has no existing test framework, `package.json` test script, or CI test step. Introducing test infrastructure for a single button is disproportionate.
- **Alternatives considered**:
  - *Add Playwright/Jest for this feature only* — rejected: would be the first test tooling in the project, unrelated in scope to this feature.
