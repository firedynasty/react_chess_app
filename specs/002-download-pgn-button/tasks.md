---

description: "Task list template for feature implementation"
---

# Tasks: Download PGN Button

**Input**: Design documents from `/specs/002-download-pgn-button/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/download-pgn.md, quickstart.md (all present)

**Tests**: Not requested for this feature. `index.html` has no existing test framework/build step (see research.md); validation is manual, per `quickstart.md`, called out in the Polish phase below instead of per-story test tasks.

**Organization**: Tasks are grouped by user story (spec.md: US1 = P1, US2 = P2, US3 = P2) so each can be implemented and independently verified.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can be worked on in parallel (touches a different, non-overlapping region of `index.html` with no dependency on another pending task)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All file paths are exact; this is a single-file feature — every task edits `index.html`

## Path Conventions

- **Single-file static web app** (existing architecture, no build step): all changes land in `index.html` at the repository root. No new files or directories are created by this feature.

## Phase 1: Setup

**Purpose**: Confirm the insertion points plan.md/contracts assume are still accurate before editing (line numbers can drift as the file evolves).

- [X] T001 In `index.html`, confirm the following anchors still match plan.md's line references (adjust the task descriptions below if they've shifted): `<button id="copyPgnBtn" onclick="copyPgnToClipboard()">` in the toolbar (~line 1204), `function moveTreeToPgn(rootNode)` (~line 3162) and `function copyPgnToClipboard()` (~line 3214) in the `<script>` section, and `fenQueueDownload()` (~line 8795-8814, the existing Blob/`URL.createObjectURL`/anchor-`download` pattern this feature reuses).

**Checkpoint**: Insertion points confirmed — safe to proceed to Foundational.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared plumbing every user story needs — the button that triggers the feature, and the generic file-save mechanics none of the stories can work without.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] In `index.html`, add a `<button id="downloadPgnBtn" onclick="downloadPgn()">Download PGN</button>` immediately after the existing `<button id="copyPgnBtn" ...>Copy PGN</button>` in the toolbar (~line 1204), styled consistently with adjacent toolbar buttons (see contracts/download-pgn.md "UI contract: button").
- [X] T003 [P] In `index.html`, add a `triggerPgnFileDownload(pgnText)` helper function next to `copyPgnToClipboard()` (~line 3241) that: (a) computes a filename per data-model.md "Value: Download Filename" — prefix `game_`, a timestamp derived from `new Date().toISOString()` with `:` and `T` replaced (e.g. via `.slice(0, 19).replace(/[:T]/g, '-')`), extension `.pgn`; (b) builds a `Blob` from `pgnText` with type `application/x-chess-pgn`; (c) creates a throwaway `<a>` element, sets `href` to `URL.createObjectURL(blob)` and `download` to the computed filename, calls `.click()`, then `URL.revokeObjectURL(...)` — mirroring `fenQueueDownload()` (`index.html:8795-8814`). This function takes PGN text as a parameter and contains no PGN-resolution logic of its own — it is pure, story-agnostic file-save plumbing shared by every story below.

**Checkpoint**: Button exists and the generic download mechanic is ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Download the currently loaded game as a PGN file (Priority: P1) 🎯 MVP

**Goal**: Clicking "Download PGN" with a game loaded saves a `.pgn` file to disk containing the current game's moves/variations/comments, reflecting any in-session edits, with a unique filename per download.

**Independent Test**: Load any game, click "Download PGN", and confirm a `.pgn` file is saved to the browser's downloads location containing the exact moves and variations currently shown in the move table (per quickstart.md Scenario 1).

### Implementation for User Story 1

- [X] T004 [US1] In `index.html`, implement `downloadPgn()` next to `triggerPgnFileDownload()` (~line 3241+): resolve PGN text using the identical priority order `copyPgnToClipboard()` uses — `window.moveTree ? moveTreeToPgn(window.moveTree) : (window.currentLoadedPgn || window.annotatedPgnWithVariations)` — pass the result to `triggerPgnFileDownload()`, then log a success message matching the app's existing `log(..., 'success')` convention (e.g. `log('PGN downloaded', 'success')`). Satisfies FR-002, FR-003, FR-004 and spec User Story 1 Acceptance Scenarios 1-3 (base download, reflects in-session edits, distinct filenames on repeat clicks — the timestamp granularity from T003 already covers this).

**Checkpoint**: User Story 1 is fully functional and independently testable — this alone is a shippable MVP.

---

## Phase 4: User Story 2 - Get clear feedback when there is nothing to download (Priority: P2)

**Goal**: Clicking "Download PGN" with no game loaded produces a clear warning instead of an empty/broken file.

**Independent Test**: With no game loaded, click "Download PGN" and confirm the app surfaces a clear message and does not produce a download (per spec User Story 2 Acceptance Scenario 1).

### Implementation for User Story 2

- [X] T005 [US2] In `index.html`, add a guard at the start of `downloadPgn()` (from T004): if the resolved PGN text is falsy/empty, call `log('No PGN available to download', 'warning')` and `return` without calling `triggerPgnFileDownload()`. Satisfies FR-005 and spec SC-004 (contracts/download-pgn.md step 2).

**Checkpoint**: User Stories 1 AND 2 both work independently — no-game and has-game paths are both correct.

---

## Phase 5: User Story 3 - Downloaded PGN carries engine eval tags where available (Priority: P2)

**Goal**: When the live move tree has computed evaluations (via the existing "Get Eval" feature), the downloaded file embeds `[%eval ±x.xx]`/`#N` comments on those moves — without altering "Copy PGN"'s output or `moveTreeToPgn()` itself.

**Independent Test**: Load a game, run "Get Eval" for at least one move, click "Download PGN", and confirm the downloaded file's move-text contains a `[%eval ...]` comment on that move (per spec User Story 3 Independent Test, quickstart.md Scenario 1b).

### Implementation for User Story 3

- [X] T006 [US3] In `index.html`, add a `_fmtEvalTag(cpWhite)` helper next to `moveTreeToPgn()` (~line 3162), mirroring `chess-rag/ingest.py`'s `_fmt_eval`: if `Math.abs(cpWhite) >= 9900`, return `` `#${cpWhite > 0 ? '' : '-'}${10000 - Math.abs(cpWhite)}` ``; otherwise return `` `[%eval ${(cpWhite / 100).toFixed(2)}]` ``. Per data-model.md "Value: Eval Tag", `window.positionEvalMap` already encodes mate scores the same way (`scoreValue > 0 ? 10000 - scoreValue : -10000 - scoreValue`), so no conversion beyond formatting is needed.
- [X] T007 [US3] In `index.html`, add `moveTreeToPgnWithEvals(rootNode)` next to `moveTreeToPgn()` (~line 3162-3212): duplicate `moveTreeToPgn()`'s traversal (`writeMoveHead`/`serializeNode`/`serializeChildren`) exactly, with one addition inside the head-writing step — if `window.positionEvalMap[node.fen] !== undefined`, compute `_fmtEvalTag(window.positionEvalMap[node.fen])` (from T006) and append it to the node's comment text (space-separated if `node.comment` is already set) before it is wrapped in `{...}`. Must be read-only against `window.positionEvalMap` and every Move Node field — no node's `comment` property is mutated, only the returned string differs (data-model.md "State transitions"; contracts/download-pgn.md "Function contract: moveTreeToPgnWithEvals"). Do **not** modify `moveTreeToPgn()` itself — it must keep serving `copyPgnToClipboard()` unchanged (FR-006, research.md decision).
- [X] T008 [US3] In `index.html`, update `downloadPgn()` (from T004) to call `moveTreeToPgnWithEvals(window.moveTree)` instead of `moveTreeToPgn(window.moveTree)` in its tree-branch PGN resolution. The fallback branch (`window.currentLoadedPgn || window.annotatedPgnWithVariations`) stays unchanged — no eval tags are attached in that path, per spec Assumptions (no live tree means no per-node FEN to look up). Satisfies FR-007, FR-008, FR-009.

**Checkpoint**: All three user stories are independently functional — base download, empty-state warning, and eval-tag embedding.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation across all stories together.

- [X] T009 Run the full `quickstart.md` validation for `002-download-pgn-button` in a browser (Scenario 1, Scenario 1b, and the empty-state case from spec User Story 2) per `quickstart.md`'s Setup instructions. Confirm SC-001 through SC-005 all hold, and that `copyPgnToClipboard()` / `#copyPgnBtn` behavior is byte-for-byte unchanged from before this feature (FR-006).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories.
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion.
  - US1 (Phase 3) has no dependency on US2 or US3.
  - US2 (Phase 4) modifies the same `downloadPgn()` function US1 created (T004) — depends on T004, but is otherwise independent in behavior (only adds the empty-state guard).
  - US3 (Phase 5) also modifies `downloadPgn()` (T004) and adds two new functions — depends on T004, independent of US2's guard (T005) in effect, though both edit the same function body so should land sequentially, not concurrently.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2). No dependencies on other stories.
- **User Story 2 (P2)**: Can start after Foundational; builds directly on US1's `downloadPgn()` (T004) since the guard is added inside that same function.
- **User Story 3 (P2)**: Can start after Foundational; also builds on US1's `downloadPgn()` (T004), but its two new functions (T006, T007) are self-contained and only wired in at the last step (T008).

### Within Each User Story

- US1: single implementation task (T004) — no internal ordering beyond itself.
- US2: single implementation task (T005), sequential after T004.
- US3: T006 (helper) before T007 (uses the helper) before T008 (wires it into `downloadPgn()`, which must already exist from T004).

### Parallel Opportunities

- T002 and T003 (Foundational) touch disjoint regions of `index.html` (toolbar markup vs. a new `<script>` function) with no dependency on each other — can be done in parallel.
- Beyond Foundational, this is a small single-file feature where most remaining tasks sequentially edit the same `downloadPgn()` function body or its immediate neighbors — genuine parallelism is limited. Do not parallelize T004-T008; land them in order to avoid merge conflicts within the same function.

---

## Parallel Example: Foundational Phase

```bash
# Launch both Foundational tasks together (different regions of index.html):
Task: "Add Download PGN button next to #copyPgnBtn in the toolbar (~line 1204)"
Task: "Add triggerPgnFileDownload(pgnText) helper next to copyPgnToClipboard() (~line 3241)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001).
2. Complete Phase 2: Foundational (T002, T003) — blocks everything else.
3. Complete Phase 3: User Story 1 (T004).
4. **STOP and VALIDATE**: Run quickstart.md Scenario 1 manually — a real "Download PGN" button that saves a correct, uniquely-named `.pgn` file. This is a shippable MVP even before US2/US3 land.

### Incremental Delivery

1. Setup + Foundational → button and file-save mechanics exist.
2. Add User Story 1 (T004) → base download works → validate → ship.
3. Add User Story 2 (T005) → empty-state warning added → validate → ship.
4. Add User Story 3 (T006-T008) → eval tags embedded → validate (quickstart Scenario 1b, including the diff-against-Copy-PGN check) → ship.
5. Polish (T009) → full quickstart pass across every scenario.

---

## Notes

- [P] tasks touch different, non-overlapping parts of `index.html` and have no dependency on each other.
- [Story] label maps each task to its user story from spec.md for traceability.
- No automated tests exist or are requested for this project (see research.md) — validation is manual via `quickstart.md`, consolidated into T009 rather than per-story test tasks.
- Since every task edits the single `index.html` file, commit after each task (or logical group, e.g. after each user story's checkpoint) rather than batching unrelated edits together.
- Verify each checkpoint (end of Phases 2-5) manually in a browser before moving on, per the relevant quickstart.md scenario.

## Implementation Notes (post-hoc)

- T004 and T008 landed as a single edit: `downloadPgn()` was written directly against `moveTreeToPgnWithEvals()` rather than staging through `moveTreeToPgn()` first, since T006/T007 were implemented in the same pass. Functionally equivalent to doing them in strict order; all tasks still verified individually.
- T009 was executed with real browser automation (Claude in Chrome) against a local `python3 -m http.server`, not just code review: loaded the quickstart test PGN, confirmed `downloadPgn()`/`moveTreeToPgnWithEvals()`/`_fmtEvalTag()`/`triggerPgnFileDownload()` all exist and work, verified byte-identical output to `moveTreeToPgn()` when no evals exist (SC-003 baseline), verified eval tags append correctly alongside existing comments and format mate scores correctly, verified the empty-state warning path produces no download, verified 3 rapid downloads get 3 distinct timestamped filenames (SC-002), and clicked the real toolbar buttons (not just called the JS functions) to exercise the actual `onclick` wiring. No console errors were introduced.
- Discovered (not fixed, out of scope): `#copyPgnBtn` is a duplicate DOM id — it also exists on an unrelated button in the top "Input" panel (`index.html:743`) with its own separate click listener (`index.html:9020-9038`) that reads from `#pgnInput` directly. `document.getElementById('copyPgnBtn')` resolves to that first, unrelated button. This predates this feature and doesn't affect `downloadPgn()`/`copyPgnToClipboard()` (which fire via the toolbar button's inline `onclick`, not `getElementById`), but is worth a follow-up cleanup ticket since it could bite a future `getElementById('copyPgnBtn')` caller.
