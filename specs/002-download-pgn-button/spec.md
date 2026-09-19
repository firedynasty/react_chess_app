# Feature Specification: Download PGN Button

**Feature Branch**: `002-download-pgn-button`

**Created**: 2026-09-19

**Status**: Draft

**Input**: User description: "Add a "Download PGN" button next to the existing "Copy PGN" button in index.html. It should let the user download the current game's PGN (including variations) as a .pgn file, using the same PGN source-of-truth logic as the existing copyPgnToClipboard function (prefer the live window.moveTree serialized via moveTreeToPgn, falling back to window.currentLoadedPgn or window.annotatedPgnWithVariations). The downloaded file should be named with a timestamp so repeated downloads don't collide." Follow-up: "when I download pgn needs to have eval tags" — the downloaded file must additionally embed `[%eval ±x.xx]` comments (standard PGN eval-tag format, matching the `chess-rag/ingest.py` annotation pipeline's convention) for moves that already have a computed engine evaluation in this browser session, sourced from the app's existing `window.positionEvalMap`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Download the currently loaded game as a PGN file (Priority: P1)

A user has a game (with or without variations and annotations) loaded and displayed on the board/move table. Instead of copying the PGN to the clipboard and pasting it elsewhere, they want a file they can save directly to disk — e.g. to archive it, attach it to a message, or import it into another chess tool.

**Why this priority**: This is the entire feature. Without it there is nothing to test or ship.

**Independent Test**: Load any game, click "Download PGN", and confirm a `.pgn` file is saved to the browser's downloads location containing the exact moves and variations currently shown in the move table.

**Acceptance Scenarios**:

1. **Given** a game is loaded and displayed in the move table, **When** the user clicks "Download PGN", **Then** a `.pgn` file downloads containing the full move text (including any variations and comments) currently reflected on screen.
2. **Given** the user has made edits to the move tree (e.g. added a variation or annotation) since the game was first loaded, **When** the user clicks "Download PGN", **Then** the downloaded file reflects those edits, not the originally loaded PGN.
3. **Given** the user downloads the same game twice in a row, **When** both downloads complete, **Then** the two files have different filenames (no overwrite/collision) so both are retained on disk.

---

### User Story 2 - Get clear feedback when there is nothing to download (Priority: P2)

A user clicks "Download PGN" before any game has been loaded (empty session).

**Why this priority**: Prevents a confusing silent failure or a broken empty-file download; matches the existing "Copy PGN" behavior for the same edge case.

**Independent Test**: With no game loaded, click "Download PGN" and confirm the app surfaces a clear message and does not produce a download.

**Acceptance Scenarios**:

1. **Given** no game/PGN has been loaded, **When** the user clicks "Download PGN", **Then** no file is downloaded and the user sees a message indicating there is no PGN available.

---

### User Story 3 - Downloaded PGN carries engine eval tags where available (Priority: P2)

A user has run "Get Eval" on the loaded game (or some of its positions) before downloading, so the app already holds computed centipawn scores for those positions. They want the downloaded file to preserve that analysis — e.g. so it can be re-opened later, or fed into another tool (such as `chess-rag`'s ingest pipeline) that understands standard `[%eval ...]` PGN comments — instead of losing it the moment they leave the page.

**Why this priority**: Builds on User Story 1 (the download must exist first); this is the specific enhancement the user asked for on top of the base download, so it ships alongside P1, not as a "maybe later."

**Independent Test**: Load a game, run "Get Eval" for at least one move, click "Download PGN", and confirm the downloaded file's move-text contains a `[%eval ...]` comment on that move.

**Acceptance Scenarios**:

1. **Given** the user has run "Get Eval" and one or more positions in the current game have a computed evaluation, **When** the user clicks "Download PGN", **Then** each such move in the downloaded file carries a `[%eval ±x.xx]` comment (or `#N` for a forced mate), reflecting that position's White-perspective centipawn score.
2. **Given** a move in the game has no computed evaluation (evals were never run, or only run for part of the game), **When** the user clicks "Download PGN", **Then** that move downloads without an `[%eval ...]` comment — no error, no placeholder value, no blocked download.
3. **Given** a move already has a user-entered annotation/comment (e.g. `?!` with a note), **When** the download includes an eval tag for that same move, **Then** the eval tag is appended alongside the existing annotation/comment rather than replacing it.

---

### Edge Cases

- What happens when the user clicks "Download PGN" with no game loaded? → Same-style warning as "Copy PGN" today; no file is produced (see User Story 2).
- What happens when the loaded game has no variations, only a mainline? → The downloaded file contains just the mainline moves, same as "Copy PGN" would copy.
- What happens if the user clicks "Download PGN" repeatedly within the same second? → Filenames still remain unique enough that no download silently overwrites another in the browser's download folder (see SC-002).
- What happens when no evaluations have been computed at all for the current game? → The download still succeeds; it simply contains no `[%eval ...]` tags (see User Story 3, Scenario 2).
- What happens when the game came from the non-tree fallback (`window.currentLoadedPgn`/`window.annotatedPgnWithVariations`, no live `window.moveTree`)? → No per-move position data is available to attach evals to in that path, so the download proceeds without eval tags, same as if no evals existed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a "Download PGN" control next to the existing "Copy PGN" control.
- **FR-002**: When activated with a game loaded, the system MUST produce a downloadable `.pgn` file containing the current game's moves, including variations and any comments/annotations, using the same source of truth the "Copy PGN" feature uses today (current in-memory move tree if present, otherwise the most recently loaded PGN text).
- **FR-003**: The generated file MUST use the standard `.pgn` file extension.
- **FR-004**: Each download's filename MUST include a timestamp (or equivalent unique value) so that consecutive downloads of the same or different games do not produce identical filenames.
- **FR-005**: When activated with no game/PGN currently available, the system MUST NOT produce a file download and MUST inform the user that there is nothing to download.
- **FR-006**: The feature MUST NOT alter or interfere with the existing "Copy PGN" (clipboard) behavior — eval tags described below apply only to the downloaded file, never to the clipboard output.
- **FR-007**: For each move in the downloaded game that has a computed engine evaluation available (from the app's existing per-position evaluation data), the system MUST embed a standard PGN `[%eval ±x.xx]` comment (or `#N` for a mate score) on that move, appended alongside any existing annotation/comment rather than replacing it.
- **FR-008**: For a move with no computed evaluation available, the system MUST download that move without an eval tag — this MUST NOT block the download, produce an error, or substitute a placeholder value.
- **FR-009**: Eval-tag values MUST be derived only from evaluations the app has already computed in the current session (no new engine analysis is triggered by clicking "Download PGN" itself).

### Key Entities

- **PGN Export Text**: The serialized move-text (SAN moves, move numbers, variations in parentheses, comments in braces, and — for downloads — `[%eval ...]` tags) representing the currently active game state.
- **Position Evaluation Data**: The app's existing per-position engine-evaluation store (populated by the existing "Get Eval" feature), keyed by board position, giving a White-perspective centipawn (or mate) score. This feature reads it but does not modify it or trigger new evaluations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from "game on screen" to "PGN file saved to disk" in a single click, with no intermediate dialogs or copy/paste steps.
- **SC-002**: Downloading the same game 5 times in a row results in 5 distinct files on disk, none of which overwrite a previous one.
- **SC-003**: The moves, move numbers, variations, and user-entered annotations/comments in the downloaded file are identical to what "Copy PGN" would place on the clipboard at the same moment; the only permitted difference is the presence of `[%eval ...]` tags in the download.
- **SC-004**: Attempting to download with nothing loaded produces a clear on-screen message instead of an empty or broken file.
- **SC-005**: Every move with a previously computed evaluation is verifiably tagged in the downloaded file (spot-checkable by opening the file and comparing against the app's own eval display for the same position); every move without one downloads cleanly with no tag.

## Assumptions

- Reuses the existing PGN serialization already used by "Copy PGN" (live move tree preferred, falling back to the last-loaded PGN text) rather than introducing a second, separate way of deriving PGN text.
- Eval tags are only attachable when the live in-memory move tree is the PGN source (each move needs an associated position to look up its evaluation); the fallback text-only path (no live tree) downloads without eval tags, same as when no evaluations exist at all.
- No new engine analysis is performed for this feature — it only surfaces evaluations the user already generated via the existing "Get Eval" feature in the current session.
- Only the raw `[%eval ...]` value is embedded — no move-quality glyphs (`?`, `??`, `?!`) or embedded "best line" variations are derived from the eval data as part of this feature (that heavier analysis already exists separately in `chess-rag/ingest.py`'s offline pipeline and is out of scope here).
- Runs entirely client-side in the browser, consistent with the rest of this single-page app — no server round-trip is introduced.
- One file per click, containing exactly one game (no batch/multi-game export in scope).
- Filename uniqueness only needs to hold for downloads triggered within the same browser session on the same machine; no cross-device uniqueness guarantee is required.
