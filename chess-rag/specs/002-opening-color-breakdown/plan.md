# Implementation Plan: Opening Color Column

**Branch**: `002-opening-color-breakdown` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-opening-color-breakdown/spec.md`

## Summary

The Openings Stats table in `tree_viewer.html` currently aggregates games into one row per (ECO, opening name), silently mixing White and Black games together when an opening was played as both. Re-key the aggregation to (ECO, opening name, color) so every row is always scoped to a single color, add a sortable Color column, and propagate the color dimension through every place a row's identity is used today (pinning, the per-opening detail modal, the "Together" combined view). Purely a client-side JS change inside the HTML template that `tree_viz.py` emits — no new data fields are needed since `my_color` is already present on every game record.

## Technical Context

**Language/Version**: Python 3 (generator script) emitting a single self-contained HTML file with inline JS (ES2017-class browser JS, no build step)

**Primary Dependencies**: None beyond what's already embedded in `tree_viz.py`'s `HTML_TEMPLATE` (vanilla JS, no framework)

**Storage**: N/A — data is the `PGNS` object embedded directly in the generated HTML (per-bucket `data/<key>/games.pgn`, parsed by `load_pgns()` in `tree_viz.py`)

**Testing**: Manual verification via regenerating `tree_viewer.html` for a bucket with mixed-color openings and exercising the UI in a browser (project has no automated JS test harness)

**Target Platform**: Static HTML file opened in a browser (or served statically); regenerated per bucket by running `python tree_viz.py <key>` (or equivalent existing invocation)

**Project Type**: Single generated-artifact web page (no frontend/backend split)

**Performance Goals**: N/A — table has at most a few hundred rows per bucket; no perceptible re-render cost from doubling row count in the worst case (every opening split into two rows)

**Constraints**: Must not change the `PGNS` embedded-data schema or `load_pgns()` output shape (color split is a pure presentation/aggregation change downstream of existing `my_color` field); must not regress existing filters (time control, date range, opening-name search) or the pin/"Together" flows

**Scale/Scope**: Single file (`tree_viz.py`, ~1900 lines, mostly one big `HTML_TEMPLATE` string); touches ~10 JS functions inside that template plus one Python helper (`buildOpeningStats` is actually already JS — no Python-side change needed at all, since `my_color` is already per-game data)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No `.specify/memory/constitution.md` principles are defined for this project (template is unfilled) — no gates apply.

## Project Structure

### Documentation (this feature)

```text
specs/002-opening-color-breakdown/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet created)
```

No `contracts/` directory: this feature has no external interface (no API, no CLI flag, no schema other party depends on) — it's a self-contained change to one HTML page's embedded JS.

### Source Code (repository root)

```text
chess-rag/
└── tree_viz.py           # Generator script; HTML_TEMPLATE string (~line 255 onward)
                           # contains all JS touched by this feature:
                           #   buildOpeningStats()   — row aggregation, add color to key
                           #   sortOpenings()         — add 'color' sort case
                           #   renderOpenings()       — add Color <th>/<td>, header sort arrow
                           #   openOpModal()          — key by (eco,name,color), filter games by color
                           #   pinCurrentOp()          — _pinnedOps entries gain `color`
                           #   toggleOpPin()           — same
                           #   updatePinnedTabs()      — pinned-tab label/lookup keyed by color too
                           #   openOpByKey()           — 3-part key parse
                           #   renderTogether()        — per-pinned-opening game filter by color
                           #   _pinnedOps / _opRows / _currentOpKey — state shape gains `color`
```

**Structure Decision**: Single-file change. No new files. All edits land inside `tree_viz.py`'s `HTML_TEMPLATE` (client-side JS) except where noted; the Python-side `load_pgns()` already exposes `my_color` per game, so no Python data-model change is required.

## Complexity Tracking

*No constitution violations — table not needed.*
