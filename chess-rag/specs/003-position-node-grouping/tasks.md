---

description: "Task list for Position Column and Transposition Merging (003-position-node-grouping)"
---

# Tasks: Position Column and Transposition Merging for Opening Stats

**Input**: Design documents from `/specs/003-position-node-grouping/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md. Builds on Feature 002 (already implemented) — the color split stays; this feature changes what the *rest* of the row key is.

**Tests**: Not requested — verification is scripted/manual, via the Phase 6 task.

**Organization**: Tasks are grouped by user story. Almost all touch `chess-rag/tree_viz.py` (one Python function, plus the same JS functions 002 already modified). All file paths are relative to `chess-rag/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different functions, no ordering dependency)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Phase 1: Setup

None needed — existing, already-running code.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Change row identity from Feature 002's `eco|name|color` to `positionKey|color`, and derive the values every later phase needs (`positionKey`, `positionText`). Per data-model.md, `eco`/`name` move from being part of the identity to being display-only fields (safe, per research.md's proof that name is a pure function of position on real data).

**⚠️ CRITICAL**: Must be complete before Phase 3/4/5 — those phases render/sort/search fields this phase creates, and reusing 002's `eco|name` identity here would keep the over-merging bug research.md documents.

- [X] T001 In `tree_viz.py`'s `load_pgns()` (Python, not the JS template), add a `"position_key": _fen_to_key(opening_fen) if opening_fen else None` field to each game's dict, reusing the existing `_fen_to_key()` helper (already defined above `load_eco_data()`) — per data-model.md's `PGNS[id]` table.
- [X] T002 In `tree_viz.py`'s `HTML_TEMPLATE`, update `buildOpeningStats(nameFilter)`: compute `const positionKey = g.position_key || '__no_match__';` (sentinel for the null/no-ECO-match bucket, so those games still group into one row as they do today), change the grouping key to `` `${positionKey}|${color}` ``, and when first creating a row for a key, seed `eco`/`name` from that game (display-only now) and compute `positionText` by the same most-common-move-sequence tie-break `openOpModal()` already uses (count `(g.opening_moves || []).join(' ')` across the row's contributing games, take the most frequent) — per data-model.md's Opening Stats Row table.
- [X] T003 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `openOpModal(i)`: read `positionKey` from `_opRows[i]` instead of `eco`/`name` for identity, change `_currentOpKey` to `` `${positionKey}|${color}` ``, change the pinned-check to match on `p.positionKey === positionKey && p.color === color`, and change the games lookup to `g.position_key === positionKey (or the '__no_match__' sentinel) && g.my_color === color` instead of matching on `g.eco`/`g.opening` text — per FR-005.
- [X] T004 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `pinCurrentOp()`: `_currentOpKey` now splits into exactly 2 parts (`positionKey`, `color`) via `lastIndexOf('|')` — simpler than 002's 3-part split since `eco`/`name` are no longer in the key. Pull `eco`, `name`, `positionText` from the currently-open row/modal state to store as display-only fields on the pushed `_pinnedOps` entry alongside `positionKey`/`color`.
- [X] T005 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `toggleOpPin(i, evt)`: match/push against `_pinnedOps` using `r.positionKey` and `r.color`; carry `r.eco`, `r.name`, `r.positionText` onto the pushed entry as display-only fields.
- [X] T006 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `updatePinnedTabs()`: destructure `positionKey`, `color`, `eco`, `name` from each `_pinnedOps` entry; build the `openOpByKey` call as `` `${positionKey}|${color}` ``; tab label keeps showing `eco`/`name` (display-only, unchanged visually).
- [X] T007 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `openOpByKey(key)`: parse as 2 parts (`positionKey`, `color`) via `lastIndexOf('|')`, match `_opRows` on `r.positionKey === positionKey && r.color === color`.
- [X] T008 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `renderTogether()`: destructure `positionKey`, `color`, `eco`, `name` from each `_pinnedOps` entry; change the per-game filter to `g.position_key === positionKey (sentinel-aware) && g.my_color === color` instead of matching `g.eco`/`g.opening` text; table row still displays `eco`/`name`/`color` as before (002's Color column stays).

**Checkpoint**: Rows are now correctly keyed by exact position + color everywhere pin/modal/Together touch them. Not yet visible as a distinct "Position" column (Phase 3) — that's next.

---

## Phase 3: User Story 1 - See and sort by the position/node behind each row (Priority: P1) 🎯 MVP

**Goal**: Every row visibly shows its move sequence, sortable like the table's other columns, so rows sharing a common opening prefix land next to each other when sorted.

**Independent Test**: Regenerate `tree_viewer.html`, open Openings Stats, confirm every row shows a Position value, click its header to sort (and reverse), and confirm same-prefix rows (e.g. two different "e4 e5..." rows) land adjacent after sorting.

- [X] T009 [US1] In `tree_viz.py`'s `HTML_TEMPLATE`, update `renderOpenings()`: add a `<th class="op-sort" onclick="sortOpenings('position')">Position ${arr('position')}</th>` header and a corresponding `<td>` in the row-rendering block showing `r.positionText`.
- [X] T010 [US1] In `tree_viz.py`'s `HTML_TEMPLATE`, update `sortOpenings(col)`: add `'position'` to the columns that default to ascending (alongside `'name'`, `'eco'`, `'color'`) rather than the numeric-descending default.
- [X] T011 [US1] In `tree_viz.py`'s `HTML_TEMPLATE`, update the `rows.sort((a, b) => {...})` comparator inside `renderOpenings()`: add `if (opSortCol === 'position') return opSortDir * a.positionText.localeCompare(b.positionText);`.

**Checkpoint**: User Story 1 fully functional and independently shippable.

---

## Phase 4: User Story 2 - Key every row by its exact resulting position (Priority: P1)

**Goal**: No two rows ever represent the same exact position (over-merging eliminated), and true move-order transpositions still merge into one row. The core mechanism lands in Phase 2 (Foundational); this phase covers the one remaining edge case data-model.md flags.

**Independent Test**: Regenerate for a bucket with a coarse label spanning multiple exact positions (verified present in `data/jyan_500` — see quickstart.md scenario 2) and confirm it now splits into multiple, more precise rows whose combined totals match the original single row.

- [X] T012 [US2] In `tree_viz.py`'s `HTML_TEMPLATE`, verify the `'__no_match__'` sentinel from T002 correctly buckets every game with no ECO match into one shared row (not one row per game) — cross-check against Python: confirm `position_key` is consistently `None`/absent for exactly the same games in both `load_pgns()` (T001) and the JS grouping (T002), so the sentinel path is only hit for genuinely unmatched games.

**Checkpoint**: User Story 2 fully functional.

---

## Phase 5: User Story 3 - Find rows by typing a partial position (Priority: P2)

**Goal**: The existing openings search box also matches by position text.

**Independent Test**: Type a move-sequence fragment into the search box and confirm rows whose Position contains it appear, alongside existing name-matches.

- [X] T013 [US3] In `tree_viz.py`'s `HTML_TEMPLATE`, update `buildOpeningStats(nameFilter)`: change the existing `if (nameFilter && !name.toLowerCase().includes(nameFilter)) continue;` check so a row is kept if `nameFilter` matches *either* the opening name *or* the row's move-sequence text (computed after `positionText` is known — this may require moving the filter check to after position/text aggregation, or filtering the final `Object.values(stats)` list by `nameFilter` matching `name` or `positionText` instead of filtering per-game before aggregation).

**Checkpoint**: User Story 3 functional.

---

## Phase 6: Polish & Verification

- [X] T014 Regenerated `tree_viewer.html` for `data/jyan_500` via `python3 tree_viz.py jyan_500`. Browser tooling still unavailable this session — used the same Node-based real-execution approach as Feature 002 (harness built in the scratchpad dir this time, not /tmp). Actual results: **581 rows** (positionKey|color) vs. 545 under 002's eco|name|color keying. Game conservation: 1499 = 1499 (no games lost/duplicated). 0 rows with bad color, 0 with falsy positionKey. The 5 no-ECO-match games correctly bucket into exactly 2 sentinel rows (4 black, 1 white), not 5 separate rows — confirms T012's edge case. The previously-identified over-merged label ("D02 Queen's Pawn: London") now splits into **11 rows across 7 distinct exact positions** (was 1 row); its games still sum to 39, matching the original combined total. Found **63 rows** in the real dataset where contributing games used more than one distinct move order (genuine transposition merges), e.g. one row combining "c3 e5 d4 exd4 cxd4 d5 Nc3 Nf6 Nf3" and "d4 d5 c4 e6 cxd5 exd5 Nc3 Nf6 Nf3" into a single row — direct proof FR-003/FR-004/SC-001 work on real data. Sorting by Position: all 62 "e4 e5..." rows land fully contiguous after sort (span 454–515, no gaps). Search-by-position (T013): typing "e4 e5" returns 65 matching rows, 100% verified to match on name or position text. Full embedded `<script>` (34.75MB) passes `node --check`. Static grep confirms zero remaining `eco===...&&name===` identity comparisons anywhere in `tree_viz.py`. Not verified: actual visual rendering (Position column CSS/layout) and literal click interactions — recommend a quick manual open in a browser before considering this fully done, same caveat as 002.

---

## Dependencies

- **Phase 2 (Foundational)** blocks Phases 3, 4, and 5 — all of them read `positionKey`/`positionText` fields Phase 2 creates.
- **Phase 3 (US1)** and **Phase 5 (US3)** both need `positionText` (from T002) but are otherwise independent of each other.
- **Phase 4 (US2)**'s one remaining task (T012) is a verification/edge-case check, not new plumbing — it can run any time after Phase 2.
- **Phase 6** depends on all prior phases.

## Parallel Execution Examples

- T003–T008 (Phase 2) touch six different functions with no shared state beyond the key format T001/T002 already define, and can be done in parallel.
- T009–T011 (Phase 3) and T013 (Phase 5) are independent of each other in terms of logic, though both build on T002.

## Implementation Strategy

**MVP = Phase 2 + Phase 3** (User Story 1): delivers a visible, sortable Position column with correct underlying position-based grouping — the direct, concrete ask. Phase 4's remaining edge case and Phase 5's search extension are small, low-risk fast-follows.
