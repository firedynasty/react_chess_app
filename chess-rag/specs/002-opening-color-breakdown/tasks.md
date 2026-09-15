---

description: "Task list for Opening Color Column (002-opening-color-breakdown)"
---

# Tasks: Opening Color Column

**Input**: Design documents from `/specs/002-opening-color-breakdown/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not requested for this feature — verification is manual, via the Phase 5 task against `quickstart.md`.

**Organization**: Tasks are grouped by user story. All tasks touch a single file, `chess-rag/tree_viz.py`, specifically the JS inside its `HTML_TEMPLATE` string (the client-side code that renders `tree_viewer.html`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different functions, no ordering dependency)
- **[Story]**: Which user story this task belongs to (US1, US2)
- All file paths are relative to `chess-rag/`

## Phase 1: Setup

No project-initialization work needed — this is a change to existing, already-running code with no new dependencies, build step, or scaffolding.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Change the row identity from `eco|name` to `eco|name|color` everywhere it's used, so that once rows are split by color (Phase 3), every downstream feature (detail modal, pinning, "Together" view) stays correct instead of silently merging or crashing on duplicate keys.

**⚠️ CRITICAL**: Must be complete before Phase 3 — splitting rows by color without this produces two rows with colliding pin/modal identity.

- [X] T001 In `tree_viz.py`'s `HTML_TEMPLATE`, update the `buildOpeningStats(nameFilter)` function: change the aggregation key from `` `${eco}|${name}` `` to include `g.my_color` (`` `${eco}|${name}|${color}` ``), add `color: g.my_color` to each row object per data-model.md's Opening Stats Row shape, and update the state comments for `_opRows`, `_pinnedOps`, `_currentOpKey` (around the `let opSortCol = 'games';` block) to note the 3-part key.
- [X] T002 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `openOpModal(i)`: derive `color` from `_opRows[i]`, change `_currentOpKey` to the 3-part key, change the pinned-check (`_pinnedOps.some(...)`) to also match `p.color === color`, and change the games lookup (`Object.entries(PGNS).filter(...)`) to also require `g.my_color === color` per FR-005.
- [X] T003 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `pinCurrentOp()`: parse `_currentOpKey` as a 3-part key (eco, name, color), and match/push against `_pinnedOps` using all three fields.
- [X] T004 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `toggleOpPin(i, evt)`: read `color` from `_opRows[i]` and match/push against `_pinnedOps` using `eco`, `name`, and `color`.
- [X] T005 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `updatePinnedTabs()`: destructure `color` from each `_pinnedOps` entry, include it in the pinned-tab's `onclick` call to `openOpByKey`, and use a 3-part key throughout.
- [X] T006 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `openOpByKey(key)`: parse the key as 3 `|`-separated parts (eco, name, color) instead of 2, and match `_opRows` on all three fields.
- [X] T007 [P] In `tree_viz.py`'s `HTML_TEMPLATE`, update `renderTogether()`: destructure `color` from each `_pinnedOps` entry in the `for (const { eco, name } of _pinnedOps)` loop, and add `g.my_color === color` to the per-game filter condition (`if ((g.eco || '—') !== eco || (g.opening || 'Unknown') !== name) continue;`) so each pinned row's combined total reflects only its own color.

**Checkpoint**: Foundational key-propagation complete. Rows aren't visibly split yet (that's Phase 3), but nothing will break once they are.

---

## Phase 3: User Story 1 - See which color each row's stats belong to (Priority: P1) 🎯 MVP

**Goal**: Every opening row is visibly and unambiguously scoped to one color; an opening played as both colors renders as two separate rows.

**Independent Test**: Regenerate `tree_viewer.html` for a bucket with a White-only opening, a Black-only opening, and an opening played as both. Confirm the White-only and Black-only openings each show one row with a clear color indicator, and the mixed opening shows two rows (one White, one Black) whose combined totals match what was previously one row.

- [X] T008 [US1] In `tree_viz.py`'s `HTML_TEMPLATE`, update `renderOpenings()`: add a `<th>Color</th>` column header (placed before or after ECO, matching the row markup below) to the table generated in the `html += ...` block.
- [X] T009 [US1] In `tree_viz.py`'s `HTML_TEMPLATE`, update the row-rendering `rows.forEach((r, i) => {...})` block inside `renderOpenings()`: add a `<td>` showing a compact color indicator for `r.color` (e.g. a colored glyph/short label distinguishing White vs Black at a glance), per FR-002/FR-003 — visible directly in the row, no click required.
- [X] T010 [US1] In `tree_viz.py`'s `HTML_TEMPLATE`, verify (and adjust if needed) that the CSS already covering `.eco-badge`/table cell styling extends cleanly to the new Color cell — add a small dedicated style rule only if the existing table/badge CSS doesn't already produce a legible result.

**Checkpoint**: User Story 1 fully functional — rows are color-scoped and visibly labeled. This alone is shippable.

---

## Phase 4: User Story 2 - Sort by color to review one side of the repertoire together (Priority: P2)

**Goal**: Clicking the Color column header sorts rows so same-color rows group together, using the same interaction as the table's existing sortable columns.

**Independent Test**: With Phase 3 in place, click the Color column header and confirm all White rows sort together and all Black rows sort together; click again to reverse; click a different header afterward and confirm it takes over the sort as usual.

- [X] T011 [US2] In `tree_viz.py`'s `HTML_TEMPLATE`, update `sortOpenings(col)`: no change needed to the toggle logic itself (it's already generic on `col`), but confirm `opSortCol === col` comparisons work for `'color'` — add a default direction if `color` should behave like `name`/`eco` (alphabetical ascending default) rather than the numeric-descending default used for `games`/`winpct`.
- [X] T012 [US2] In `tree_viz.py`'s `HTML_TEMPLATE`, update the `rows.sort((a, b) => {...})` comparator inside `renderOpenings()`: add an `if (opSortCol === 'color') return opSortDir * a.color.localeCompare(b.color);` branch (mirroring the existing `name`/`eco` string-compare branches).
- [X] T013 [US2] In `tree_viz.py`'s `HTML_TEMPLATE`, wire the Color `<th>` added in T008 with `class="op-sort" onclick="sortOpenings('color')"` and the existing `arr('color')` sort-arrow helper, matching the other sortable headers.

**Checkpoint**: User Story 2 functional — Color column sorts consistently with the rest of the table.

---

## Phase 5: Polish & Verification

- [X] T014 Regenerated `tree_viewer.html` for `data/jyan_500` (1499 real games) via `python3 tree_viz.py jyan_500`. Browser-based click-through (quickstart.md scenarios 3–5, which need live DOM interaction) was not available — the Claude in Chrome extension was declined for this session. Substituted: extracted the actual shipped `buildOpeningStats`/sort-comparator code and the embedded `PGNS` dataset from the generated HTML and executed them for real in Node against the full 1499-game dataset. Results: 545 rows (vs. 490 under the old eco|name-only key — the +55 delta exactly matches the 55 openings that were played as both colors), every row has `color` = `'white'`/`'black'` (0 bad values), total games summed across rows = 1499 = total PGNS entries (no games lost/duplicated), the per-color game-ID lookup used by the detail modal returns exactly 3 black / 4 white IDs for a sampled mixed opening matching its row counts exactly, and sorting by `color` in both directions produces one fully contiguous block per color. Full embedded `<script>` (34.6MB, all edited functions included) passes `node --check` with no syntax errors. Static grep confirmed every remaining `eco===...&&name===` comparison in `tree_viz.py` also checks `color`, and both `_pinnedOps.push` sites include it — so T003–T007 (pin/modal/Together, DOM-dependent and not directly Node-testable) are consistent with the verified logic. Not verified: actual visual rendering/CSS legibility (T010) and literal click interactions — recommend a quick manual open of `data/jyan_500/tree_viewer.html` in a browser to eyeball the Color column and pin flow before considering this fully done.

---

## Dependencies

- **Phase 2 (Foundational)** blocks Phase 3 and Phase 4 — the key-propagation must land first so split rows don't break pinning/modal/Together.
- **Phase 3 (US1)** blocks Phase 4 (US2) only in the sense that there's no Color column to sort until it exists (T008); the sort *logic* (T011–T012) could technically be written in parallel with T008–T010 but has nothing to attach to in the UI until T008 lands.
- **Phase 5** depends on Phase 3 and Phase 4 both being complete.

## Parallel Execution Examples

- T002–T007 (all in Phase 2) touch six different functions with no shared state beyond the already-defined key format from T001, and can be done in parallel once T001 lands.
- T011 and T012 (Phase 4) are independent of T008–T010 (Phase 3) in terms of *logic*, though T013 needs T008's `<th>` to exist first.

## Implementation Strategy

**MVP = Phase 2 + Phase 3** (User Story 1 only): delivers the actual reported problem — "I don't know if I'm White or Black" — as a fully working, shippable increment. Phase 4 (sorting) is a natural, low-risk fast-follow using the same infrastructure.
