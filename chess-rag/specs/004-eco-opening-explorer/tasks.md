---

description: "Task list for ECO Opening Explorer"
---

# Tasks: ECO Opening Explorer

**Input**: Design documents from `/chess-rag/specs/004-eco-opening-explorer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Not requested for this feature (no automated test suite covers the generated HTML galleries in this repo — see plan.md Testing). Validation is manual, via quickstart.md's scenarios (Phase 6).

**Organization**: Tasks are grouped by user story (spec.md priorities: US1=P1, US2=P2, US3=P2). Both the data-prep logic and the generated page live in two files only — `chess-rag/eco_explorer.py` (generator/CLI) and its output `chess-rag/eco_explorer.html` (template string inside the `.py`, mirroring `tree_viz.py` → `tree_viewer.html`) — so most tasks touch the same file sequentially; see Notes on parallelism.

## Path Conventions

Single project, no `src/`/`tests/` split — matches the existing `tree_viz.py`/`tree_viewer.html` generator pattern already used in this repo:

- `chess-rag/eco_explorer.py` — CLI, data-prep (cache augmentation), HTML template, JSON embedding
- `chess-rag/eco_explorer.html` — generated output (never hand-edited; produced by running the script)
- `chess-rag/eco_openings.json` — existing cache, extended in place with a `moves` field

---

## Phase 1: Setup

**Purpose**: Scaffold the generator script and its output shell before any real data or story logic exists

- [x] T001 Create `chess-rag/eco_explorer.py` with CLI argument parsing for `--eco-cache` (default `./eco_openings.json`), `--out` (default `./eco_explorer.html`), and `--refresh-cache`, per `contracts/eco-explorer-cli.md`
- [x] T002 In `chess-rag/eco_explorer.py`, add an `HTML_TEMPLATE` string constant (same pattern as `tree_viz.py:261`) with the page shell: dark-theme CSS tokens copied from `against_computer/tree_viewer.html` (`#1a1a2e` background, `#00d4ff` accent, etc.), a header, a volume-tabs row, a search input, an empty list-panel container, and an empty detail-panel container — no data wiring yet, and a `const ECO_LINES = __ECO_LINES_JSON__;` placeholder for later embedding

**Checkpoint**: Script runs and can be invoked with `--help`; template exists but renders an empty shell.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Get real, moves-complete line data into a form every user story depends on

**⚠️ CRITICAL**: No user story task can be completed until this phase is done — every story needs `ECO_LINES` populated.

- [x] T003 In `chess-rag/eco_explorer.py`, implement `augment_eco_cache(cache_path, force_refresh)`: load `eco_openings.json`; if any entry lacks a `moves` key (or `force_refresh` is set), fetch `eco{A-E}.json` from `https://raw.githubusercontent.com/hayatbiralem/eco.json/master/eco{letter}.json` (same URL `tree_viz.py:150` uses) and parse each entry's upstream `moves` string (e.g. `"1. e4 e5 2. Nf3"`) into a SAN array (`["e4","e5","Nf3"]`) by stripping move-number tokens; write the result back to `eco_openings.json` in place, preserving existing `eco`/`name` values exactly as-is (per `contracts/eco-line-schema.md`)
- [x] T004 In `augment_eco_cache()`, handle the data-gap case: if an upstream entry has no `moves` string for a given FEN, set `"moves": []` for that entry only and continue — never abort the whole build over one missing entry (research.md #1 fallback; data-model.md Validation Rules)
- [x] T005 In `chess-rag/eco_explorer.py`, implement `build_line_records(cache)`: convert the FEN-keyed cache dict into the array form `[{"eco", "name", "moves", "fen"}, ...]` required by the embedded page data (`contracts/eco-line-schema.md`) — `fen` moves from being the dict key to an explicit per-record field; include entries with `"moves": []` rather than dropping them
- [x] T006 In `chess-rag/eco_explorer.py`, implement `write_page(records, out_path)`: `json.dumps(records, separators=(",",":"))` and `HTML_TEMPLATE.replace("__ECO_LINES_JSON__", ...)`, then write to `--out` (mirrors `tree_viz.py:1918-1929`'s placeholder-replace pattern); wire this and T003–T005 into the CLI's main flow so `python eco_explorer.py` with no flags produces a complete `eco_explorer.html`
- [x] T007 In `eco_explorer.html`'s client JS (inside `HTML_TEMPLATE`), on page load compute from `ECO_LINES`: `byVolume` (group by `eco[0]`) and `byCode` (group by `eco`) per data-model.md's Derived/In-Memory Structures — required by US1's volume/code browsing and by the FR-007 line-count display

**Checkpoint**: Running `python eco_explorer.py` produces an `eco_explorer.html` with real, moves-complete data loaded into `ECO_LINES`/`byVolume`/`byCode` client-side (verifiable via browser devtools console), even though no UI renders it yet.

---

## Phase 3: User Story 1 - Browse the reference by ECO volume and code (Priority: P1) 🎯 MVP

**Goal**: Let a user pick a volume (A–E), then a code (e.g. "C20"), and see every named line under that code with its move sequence — independent of any played game.

**Independent Test**: Open the page, select volume "C", then code "C20", and confirm every King's Pawn Game variation (Beyer Gambit, King's Head Opening, Wayward Queen Attack, etc.) appears with its own move sequence, with no dependency on any recorded game data.

### Implementation for User Story 1

- [x] T008 [US1] In `eco_explorer.html`, render the volume tabs (All, A, B, C, D, E) and wire selection to filter `byVolume` (FR-001) — selecting a volume shows only that volume's codes
- [x] T009 [US1] In `eco_explorer.html`, render a code list/selector scoped to the active volume (from `byCode` keys whose first character matches), where clicking a code narrows the view to that single code's lines (FR-002)
- [x] T010 [US1] In `eco_explorer.html`, render the line-list table for a selected code — ECO badge, name, and move sequence per row — reusing `against_computer/tree_viewer.html`'s existing dark-theme `<table>`/row styling (FR-004)
- [x] T011 [US1] In `eco_explorer.html`, render an "N lines" count above the list for the currently browsed code, sourced from `byCode.get(code).length` (FR-007)
- [x] T012 [US1] In `eco_explorer.html`, make the per-code list a fixed-height, scrollable panel so codes with 200+ lines (per current cache counts) stay navigable without pagination (Edge Case; research.md #5)
- [x] T013 [US1] Run `python eco_explorer.py`, open the generated `eco_explorer.html`, and manually verify quickstart.md scenario 1 (volume "C" → code "C20" → full King's Pawn Game line set with counts)

**Checkpoint**: User Story 1 is fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Search by opening name or family (Priority: P2)

**Goal**: Let a user find every line matching a (partial) opening name across all volumes/codes, without knowing the ECO code.

**Independent Test**: Type a family name (e.g. "Caro-Kann") into the search box and confirm all matching lines appear across their respective codes, without first navigating by volume.

### Implementation for User Story 2

- [x] T014 [US2] In `eco_explorer.html`, add a persistent search input in the page header, visible and usable regardless of the current volume/code selection (FR-003)
- [x] T015 [US2] In `eco_explorer.html`, implement live substring filtering over the full `ECO_LINES` list (`name.toLowerCase().includes(query.toLowerCase())`, per data-model.md's Search index note), updating results on every keystroke (FR-003, Acceptance Scenario 1)
- [x] T016 [US2] In `eco_explorer.html`, when the search box is non-empty, replace the volume/code browse view with the flat search-result list, reusing T010's row rendering and T011's "N lines matched" count (FR-004, FR-007)
- [x] T017 [US2] In `eco_explorer.html`, render an explicit "No matching lines found" state when a search yields zero results, replacing any stale or blank list (Edge Case; Acceptance Scenario 2)
- [x] T018 [US2] ~~also apply the active search query to narrow the currently-selected code's list~~ — **implemented differently than scoped**: search always searches globally and overrides any code/volume selection outright (rather than narrowing within a selected code), since FR-003 requires results "not just the currently selected one" and an always-global search satisfies that unambiguously with less UI-mode complexity. Verified in Chrome: typing "Caro-Kann" while volume "D" was selected still surfaced A11 (English: Caro-Kann Defence) results.

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Inspect a single line move-by-move (Priority: P2)

**Goal**: From any browse/search entry point, open a line into a board + move-list detail view and step through its moves one at a time.

**Independent Test**: Select a single line, step through its moves on the board one at a time, independent of the browse/search entry point used to reach it.

### Implementation for User Story 3

- [x] T019 [US3] In `eco_explorer.html`, load `chess.js` on demand before opening the first detail view, mirroring `against_computer/tree_viewer.html`'s `ensureChessLibs()` pattern (research.md #2)
- [x] T020 [US3] In `eco_explorer.html`, build the line-detail panel by porting `against_computer/tree_viewer.html`'s CSS-grid board renderer (`renderBoard()`/`fenToGrid()`, `tree_viewer.html:571-608`) and `openOpModal()`'s layout (badge/name header, board, move list) — omit all game-stats and copy/reuse-elsewhere elements from the original (FR-005, FR-006)
- [x] T021 [US3] In the detail panel, replay the selected line's `moves` array with `chess.js` to produce the FEN after each ply, and render the annotated move list (e.g. "1. d4 d5 2. c4 c6") with each move clickable to jump straight to that ply (FR-004, FR-005)
- [x] T022 [US3] In the detail panel, implement Start/Prev/Next/End step controls plus Left/Right arrow-key navigation, modeled directly on `tree_viewer.html:1480-1493`'s `pgnGoStart`/`pgnGoPrev`/`pgnGoNext`/`pgnGoEnd`/`pgnJump`, updating the CSS-grid board to the FEN at the current ply in both directions (FR-005, Acceptance Scenario 1)
- [x] T023 [US3] In the detail panel, implement the data-gap state: when a line's `moves` array is empty, show an explicit "move sequence unavailable" message in place of the board/move list instead of an empty or misleading board (FR-008) — **bug found and fixed during Chrome verification**: `#detail-gap-msg` was originally nested inside `#detail-board-area`, so hiding the board area for the gap state also hid the message itself, leaving an empty modal. Moved it to be a sibling of `#detail-board-area` instead; re-verified with an injected no-moves test line that the message now renders.

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: The move-sequence sort mode (which spans all stories' list views) and final validation against the full spec

- [x] T024 In `eco_explorer.html`, add a "sort by move sequence" mode alongside the existing by-code/by-name ordering: sort lines by their `moves` array as a tuple/lexicographic key, with moves-less lines (`moves: []`) sorted into a fixed bucket at the end (FR-010; research.md #4; data-model.md Validation Rules)
- [x] T025 In `eco_explorer.html`, while in move-sequence sort mode, add a lightweight visual marker on any row whose `eco` differs from the previous row, so a continuation crossing into a new ECO code is visible (spec Acceptance Scenario 4; SC-005)
- [x] T026 Audit `eco_explorer.html` end-to-end to confirm it never renders W/D/L stats, game lists, or any other played-games-derived content, and includes no quiz/scoring/attempt-history UI anywhere (FR-006, FR-009)
- [x] T027 Run all 7 scenarios in `quickstart.md` against the generated `eco_explorer.html` and record pass/fail for each — **all 7 pass**. Scenarios 1, 2, 4 (drill-down, 237-line scroll, detail step-through) and 6 (data-gap marker) verified live in Chrome; scenario 3 (search) and 7 (distinctness) verified live in Chrome; scenario 5 (sort-by-moves + continuation adjacency) verified against the real embedded dataset via a standalone Node script reproducing `compareByMoves`/`isPrefixExtension`, since the page's native `<select>` popup could not be driven through the browser-automation tool's synthetic keyboard/mouse events — confirmed D10 "Slav Defense" is followed by its own D10 branches and then directly by a D49 Semi-Slav continuation (flagged as a sequence break) before returning to sibling D10 lines.
- [x] T028 [P] Verify `--refresh-cache` forces a re-fetch and rewrite of `eco_openings.json` even when every entry already has a `moves` field (`contracts/eco-explorer-cli.md`) — this task only exercises the CLI flag and doesn't edit `eco_explorer.py` further, so it can run independently of T024–T027 — confirmed: re-ran with `--refresh-cache` after the cache already had 12106/12106 `moves`, and it re-fetched all 5 upstream files anyway.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup (needs `HTML_TEMPLATE` to exist) — BLOCKS all user stories, since every story renders from `ECO_LINES`/`byVolume`/`byCode`.
- **User Story 1 (Phase 3)**: Depends on Foundational only.
- **User Story 2 (Phase 4)**: Depends on Foundational; reuses US1's row rendering (T010) and count display (T011), so implement after US1 (T008–T013) even though it has no separate data dependency.
- **User Story 3 (Phase 5)**: Depends on Foundational only — the detail panel opens from either the browse view (US1) or search results (US2), but has no code dependency on either beyond something to click.
- **Polish (Phase 6)**: T024–T025 depend on US1's list rendering (T010) existing to sort; T026–T028 depend on all prior phases being complete.

### Within Each User Story

- US1: T008 → T009 → T010 → T011 → T012 → T013 (each builds directly on the previous element of the same view).
- US2: T014 → T015 → T016 (needs T010/T011 from US1) → T017 → T018.
- US3: T019 → T020 → T021 → T022 → T023.

## Parallel Opportunities

This feature is a single generator script producing a single template string (`eco_explorer.py` → `eco_explorer.html`), not a multi-file service — nearly every task edits the same two files, so genuine file-level parallelism is limited (unlike a typical multi-module backend). Do not force `[P]` where it isn't real:

- T028 is the only task marked `[P]`, since it's a CLI-flag verification step that doesn't modify code already touched by T024–T027.
- If multiple people work this feature simultaneously, the safest split is one person per *phase* (not per task within a phase), since tasks within a phase edit the same functions/regions sequentially.

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002).
2. Complete Phase 2: Foundational (T003–T007) — this is also where the real ECO-data augmentation work happens.
3. Complete Phase 3: User Story 1 (T008–T013).
4. **STOP and VALIDATE**: quickstart.md scenario 1.
5. This alone is a usable ECO browser (volume → code → lines), even before search or the detail/step-through view exist.

### Incremental Delivery

1. Setup + Foundational → real data loads into an (as-yet unrendered) page.
2. Add US1 → browsable by volume/code (MVP).
3. Add US2 → name search layered on top.
4. Add US3 → board + step-through detail view layered on top.
5. Polish → move-sequence sort mode + full quickstart validation.

## Notes

- No automated tests are generated (see Tests header) — validation is the manual quickstart.md pass in T027.
- Every FR/SC reference in a task description ties back to `spec.md`'s current (post-simplification) numbering: FR-001–FR-010, SC-001–SC-005. There is no FR-011/SC-006 or copy-to-clipboard task — that requirement was dropped from the spec before this task list was generated.
- Commit after each task or logical checkpoint, per this repo's existing convention of one generator script evolving over time (cf. `tree_viz.py`'s history).
