# Quickstart: Validating the Download PGN Button

## Prerequisites

- The feature has been implemented inline in `index.html` per `plan.md` / `contracts/download-pgn.md`.
- A desktop browser (Chrome, Firefox, Safari, or Edge).

## Setup

Serve the repo root as static files and open the app — no build step:

```bash
cd /Users/stanleytan/Documents/technical/github/react-chess-analysis_vercel
python3 -m http.server 8000
# then open http://localhost:8000/index.html
```

(Opening `index.html` directly via `file://` also works for this feature, since it makes no network calls.)

## Test PGN

Paste this into the `#pgnInput` textarea and load it to the board (existing "Load to Board" flow) — it has a main line plus one variation:

```text
1. e4 e5 2. Nf3 Nc6 3. Bb5 (3. Bc4 Bc5 4. c3 Nf6) a6 4. Ba4 Nf6 5. O-O Be7
```

## Scenario 1 — Download reflects the currently loaded game (validates FR-002, SC-003)

1. With the test PGN loaded, and **before** running "Get Eval" (no evals computed yet), click **Copy PGN** and paste the clipboard somewhere visible (e.g. a scratch text field) — keep this text for comparison.
2. Click **Download PGN**.
3. **Expected**: A `.pgn` file downloads (check the browser's downloads list/folder). With no evals computed, its contents match exactly what was pasted from **Copy PGN** in step 1, including the `(3. Bc4 Bc5 4. c3 Nf6)` variation and no `[%eval ...]` tags.

## Scenario 1b — Downloaded PGN includes eval tags where computed (validates FR-007, FR-008, SC-005)

1. With the test PGN loaded, click **Get Eval** and let it compute evaluations for the game's positions.
2. Click **Download PGN**.
3. **Expected**: Opening the downloaded file in a text editor shows `[%eval ±x.xx]` (or `#N` for a forced mate) comments on the moves that have a computed evaluation. Compare a couple of values against what the app's own eval display (e.g. the eval bar, or `getEvalForLoadedPgn`'s console output) shows for the same position — they should match.
4. If evals were only computed for part of the game (e.g. you navigated away before "Get Eval" finished), **expected**: moves without a computed evaluation still appear in the file, just without an `[%eval ...]` tag — no error, no blank placeholder.
5. Click **Copy PGN** and compare its clipboard contents to the downloaded file from step 2: **expected**: identical except the clipboard version has no `[%eval ...]` tags (validates FR-006 — eval tags are download-only).

## Scenario 2 — Download reflects in-session edits, not just the originally loaded PGN

1. If `001-move-tree-context-menu` is implemented: right-click a move and add an annotation/comment (or promote a variation). If not yet implemented, skip to Scenario 3.
2. Click **Download PGN**.
3. **Expected**: The downloaded file includes the edit made in step 1 — same as **Copy PGN** would.

## Scenario 3 — Filenames don't collide across repeated downloads (validates FR-004, SC-002)

1. With a game loaded, click **Download PGN** three times in a row (a few seconds apart).
2. **Expected**: Three separate files appear in the downloads location, each with a distinct filename (no "(1)"/"(2)" browser-appended suffixes needed because the app's own timestamp already differs each time).

## Scenario 4 — No PGN loaded (validates FR-005, SC-004)

1. Open the app fresh (or otherwise get to a state where no game has been loaded — no `window.moveTree`, `window.currentLoadedPgn`, or `window.annotatedPgnWithVariations`).
2. Click **Download PGN**.
3. **Expected**: No file is downloaded. A warning message appears in the app's existing log/status area (same style as clicking **Copy PGN** in the same empty state).

## Scenario 5 — Non-interference with existing "Copy PGN" (validates FR-006)

1. With a game loaded, click **Copy PGN**.
2. **Expected**: Clipboard behavior (button flash to "Copied!", clipboard contents) is unchanged from before this feature existed.
3. Click **Download PGN** immediately after.
4. **Expected**: The download does not clear the clipboard, change `#copyPgnBtn`'s appearance, or otherwise interact with the copy flow.
