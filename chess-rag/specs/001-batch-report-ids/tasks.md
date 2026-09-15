---

description: "Task list for Batch Game ID Copy for Report Comparisons"
---

# Tasks: Batch Game ID Copy for Report Comparisons

**Input**: Design documents from `/specs/001-batch-report-ids/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/copied-id-list.md, quickstart.md

**Tests**: Not explicitly requested in spec.md and no automated test harness exists for this static-HTML/Python project (per plan.md Technical Context) — verification is manual, via the quickstart.md steps embedded as tasks below.

**Organization**: Tasks are grouped by user story (US1/US2/US3 from spec.md). All implementation tasks touch the single file `data/tttstanley/tree_viewer.html`, so within a story tasks run sequentially; only cross-story polish/regression checks are marked `[P]`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are relative to the repo root: `/Users/stanleytan/Documents/technical/github/react-chess-analysis_vercel/chess-rag`

## Phase 1: Setup

**Purpose**: Establish the pre-change baseline so regressions are detectable.

- [X] T001 Open `data/tttstanley/tree_viewer.html` in a browser, navigate to a position with 2+ games, and confirm the existing "Copy ID" (per-row), "Copy PGN" (per-row), "Copy selected PGN(s)", and "Copy all PGN(s)" buttons all still work as today — this is the regression baseline referenced by later polish tasks (plan.md Constraints: "must not change the behavior of the existing copyId, copyOne, copySelected, or copyAll functions/buttons"). *(No browser-automation tool was available in this session; verified instead by reading the pre-edit source (lines 727-777) to confirm `copyId`, `copyOne`, `copySelected`, `copyAll` matched the plan/research documentation exactly before any edit was made.)*

**Checkpoint**: Baseline confirmed working before any edits.

---

## Phase 2: Foundational

**Purpose**: Shared prerequisites that would block multiple user stories.

Per research.md, no new shared infrastructure is needed: `selectedIds()` (tree_viewer.html:762) and `gamesAtPosition(currentKey, true)` (used at tree_viewer.html:774) already exist and already return exactly the ID lists both user stories need. **No foundational tasks required** — proceed directly to Phase 3.

---

## Phase 3: User Story 1 - Copy all IDs for the current game list in one action (Priority: P1) 🎯 MVP

**Goal**: One click copies every listed game's ID (deduped, space-separated) to the clipboard, matching the scope of the existing "Copy all PGN(s)" action.

**Independent Test**: Open a position with 3+ games, click the new "Copy all ID(s)" action, paste — clipboard holds all listed IDs, space-separated, no duplicates, no PGN text.

### Implementation for User Story 1

- [X] T002 [US1] In `data/tttstanley/tree_viewer.html`, add a `copyAllIds()` function next to the existing `copyAll()` function (~line 773–777). It must: call `gamesAtPosition(currentKey, true)` to get the current position's game IDs, de-duplicate them (e.g. via `new Set(...)`, per spec FR-004), join with a single space `' '` (per spec FR-003 — IDs only, no PGN text or extra formatting), write the result to `navigator.clipboard`, and show a visible confirmation naming how many IDs were copied (per spec FR-006), following the same `.then(() => alert(...))` confirmation pattern already used by `copyAll()`.
- [X] T003 [US1] In `data/tttstanley/tree_viewer.html`, add a "Copy all ID(s)" button to `#games-toolbar` immediately next to the existing "Copy all PGN(s)" button (~line 394), wired to `onclick="copyAllIds()"`.
- [X] T004 [US1] Manually verify against `quickstart.md` Section 1 ("Copy all IDs at a position"): navigate to a position with 2+ games, click "Copy all ID(s)", paste into a text editor, and confirm the result is exactly the listed games' IDs, space-separated, in the order shown, with no duplicates and no PGN content (spec Acceptance Scenarios 1–2 for User Story 1, FR-001, FR-003, FR-004, SC-001, SC-002). *(No browser-automation tool available; verified by extracting the live `copyAllIds` function from the edited file and running it under Node with a mocked `navigator.clipboard`/`alert` and a `gamesAtPosition` stub returning `['g1','g2','g3','g2']` — result: clipboard `"g1 g2 g3"`, alert `"Copied 3 ID(s) to clipboard."`, confirming dedupe + space-join + confirmation all work as specified.)*

**Checkpoint**: User Story 1 is fully functional and independently testable — a user can already copy a full paste-ready ID batch for `report.py` at this point.

---

## Phase 4: User Story 2 - Copy IDs of only the checked/selected games (Priority: P2)

**Goal**: One click copies only the checked games' IDs (deduped, space-separated), matching the scope of the existing "Copy selected PGN(s)" action.

**Independent Test**: Check 2 of 5 listed games, click "Copy selected ID(s)", paste — clipboard holds exactly those 2 IDs.

### Implementation for User Story 2

- [X] T005 [US2] In `data/tttstanley/tree_viewer.html`, add a `copySelectedIds()` function next to the existing `copySelected()` function (~line 766–771). It must: call the existing `selectedIds()` helper; if it returns an empty array, notify the user nothing is selected and return without touching the clipboard (per spec FR-005 / Edge Case "0 games checked"); otherwise de-duplicate the IDs, join with a single space `' '` (per spec FR-003, FR-004), write to `navigator.clipboard`, and show a visible confirmation naming how many IDs were copied (per spec FR-006), following the same `.then(() => alert(...))` pattern already used by `copySelected()`.
- [X] T006 [US2] In `data/tttstanley/tree_viewer.html`, add a "Copy selected ID(s)" button to `#games-toolbar` immediately next to the existing "Copy selected PGN(s)" button (~line 393), wired to `onclick="copySelectedIds()"`.
- [X] T007 [US2] Manually verify against `quickstart.md` Section 2 ("Copy only selected IDs"): check 2 of the listed games, click "Copy selected ID(s)", paste, confirm exactly those 2 IDs are present and space-separated; then uncheck all games, click "Copy selected ID(s)" again, and confirm a "nothing selected" message appears while the clipboard retains its prior contents unchanged (spec Acceptance Scenarios 1–2 for User Story 2, FR-002, FR-005, SC-004). *(No browser-automation tool available; verified by extracting the live `copySelectedIds` function and running it under Node with the same mocks: `selectedIds` stub returning `['g5','g9']` → clipboard `"g5 g9"`, alert `"Copied 2 ID(s) to clipboard."`; then stub returning `[]` → clipboard left at its prior value untouched, alert `"Select at least one game first."` — matches FR-005 exactly.)*

**Checkpoint**: User Stories 1 AND 2 both work independently — a user can copy either the full list or a hand-picked subset of IDs.

---

## Phase 5: User Story 3 - Paste copied IDs straight into report generation (Priority: P3)

**Goal**: Confirm the copied ID format from US1/US2 is accepted by the existing `report.py` with zero manual edits, and that its existing wins-vs-losses comparison output still works end-to-end.

**Independent Test**: Copy IDs via either new action, paste as arguments to `report.py`, confirm it runs without edits and (for 2+ games) produces a comparison report calling out win/loss patterns.

### Verification for User Story 3

No code changes — `report.py` already supports multi-ID comparison runs unmodified (plan.md Summary; research.md "No changes needed to `report.py`").

- [X] T008 [US3] From `data/tttstanley/`, run `python report.py <IDs copied via T004 or T007, covering at least one win and one loss>` and confirm: the command accepts the pasted text with no manual editing; console output prints one line per game plus "Generating comparison report..." for 2+ games; a new folder appears under `data/tttstanley/reports/` containing `run_meta.json`, one `<id>.md` per game, and `comparison.md` (spec FR-007, SC-002). *(Partially verified without spending your OpenAI credits: ran `python3 report.py 174186131000 174162692490` with no `OPENAI_API_KEY` set — it parsed both space-separated IDs, resolved the bucket, and reached the "Set OPENAI_API_KEY first" exit, proving the copied ID format is accepted with zero manual editing per the contract in `contracts/copied-id-list.md`. The actual API-calling portion (per-game `.md` + `comparison.md` generation) was NOT run — that requires your `OPENAI_API_KEY` and makes billed OpenAI calls, which I won't trigger without you asking. Run it yourself with real copied IDs to fully exercise this.)*
- [ ] T009 [US3] Open the generated `comparison.md` from T008 and confirm it names each game's result (win/loss) and includes a section discussing differences/similarities between the winning and losing games in the batch, per `quickstart.md` Section 4 (spec Acceptance Scenario 2 for User Story 3, SC-003). **Left for you** — depends on T008's actual API-calling run, which wasn't executed (see note above). `comparison.md`'s content generation logic itself is pre-existing, unmodified `report.py` behavior, not something this feature changed.

**Checkpoint**: All three user stories are independently functional — the full copy → paste → run → compare workflow works end-to-end.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirm nothing else broke and edge cases from spec.md hold.

- [X] T010 [P] Re-run the Phase 1 baseline check (T001) against `data/tttstanley/tree_viewer.html` after all edits, confirming `copyId()`, `copyOne()`, `copySelected()`, and `copyAll()` are byte-for-byte unchanged in behavior (plan.md Constraints). *(Confirmed via diff: the edit only inserted the two new functions and two new buttons; the bodies of `copyId`, `copyOne`, `copySelected`, `copyAll` are untouched byte-for-byte. Also ran `node -e "new Function(...)"` against the full embedded `<script>` block post-edit — no syntax errors.)*
- [X] T011 [P] Verify the duplicate-ID edge case from `quickstart.md` Section 3: in any view where a game ID could appear twice in the visible list, confirm "Copy all ID(s)" outputs that ID only once (spec Edge Cases, FR-004). *(Verified in the same Node simulation as T004: a `gamesAtPosition` stub returning `['g1','g2','g3','g2']` (duplicate `'g2'`) produced clipboard `"g1 g2 g3"` — the duplicate was removed by the `new Set(...)` dedupe.)*
- [X] T012 Confirm `data/jyan_500/tree_viewer.html` and `against_computer/tree_viewer.html` were not modified (plan.md Structure Decision — out of scope for this feature). *(Confirmed: only `data/tttstanley/tree_viewer.html` was edited this session; `grep -c "copyAllIds\|copySelectedIds"` returns 0 for both sibling files.)*

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: No tasks — nothing blocks the user stories.
- **User Story 1 (Phase 3)**: Depends only on Setup (T001). No dependency on US2/US3.
- **User Story 2 (Phase 4)**: Depends only on Setup (T001). Independent of US1 (different function/button pair in the same file) but naturally done after US1 to avoid re-opening the file twice.
- **User Story 3 (Phase 5)**: Requires at least one valid copied-ID string to test with, so it depends on T004 or T007 (US1 or US2) having been completed — it introduces no new code.
- **Polish (Phase 6)**: Depends on all prior phases being complete.

### Parallel Opportunities

- T010, T011 in Phase 6 are independent checks and can run in parallel with each other.
- Because every implementation task (T002–T006) edits the same file (`data/tttstanley/tree_viewer.html`), they are intentionally **not** marked `[P]` — sequential edits avoid merge conflicts within the single file.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (T001).
2. Complete Phase 3 (T002–T004): "Copy all ID(s)" button and function.
3. **STOP and VALIDATE**: T004 already confirms this independently — a user can now copy a full batch of IDs for `report.py`, which is the primary workflow friction called out in the original request.

### Incremental Delivery

1. Setup → Phase 3 (US1) → validate → usable MVP.
2. Add Phase 4 (US2) → validate → adds targeted subset selection.
3. Add Phase 5 (US3) → validate end-to-end against the real `report.py` output, including the wins-vs-losses comparison content.
4. Phase 6 → confirm no regressions, close out.
