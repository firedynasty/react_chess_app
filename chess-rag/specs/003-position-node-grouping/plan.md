# Implementation Plan: Position Column and Transposition Merging for Opening Stats

**Branch**: `003-position-node-grouping` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-position-node-grouping/spec.md`

## Summary

Re-key the Openings Stats table's rows from the textual `eco|name` opening label to the exact normalized resulting-position identity already computed elsewhere in this codebase (`_fen_to_key()` applied to each game's `opening_fen`). Add a visible, sortable Position column showing the representative move sequence for each row. Extend the existing name-search box to also match position text. Builds on Feature 002 (already implemented): the color split stays, so the final row key is `position_key|color`.

One Python-side change is required (unlike 002): `load_pgns()` must emit the normalized `position_key` per game — today it only stores the full `opening_fen`, not the 4-field key `buildOpeningStats()` needs to group on.

## Technical Context

**Language/Version**: Python 3 (generator script, one new field in `load_pgns()`) + client-side JS embedded in `tree_viz.py`'s `HTML_TEMPLATE` (same as 002)

**Primary Dependencies**: `python-chess` (already a dependency, used by `_annotate_game_opening()`); no new dependencies

**Storage**: N/A — `position_key` is derived at generation time from data already parsed out of each game's PGN; no new persisted storage, no `tree.sqlite` schema change

**Testing**: Manual/scripted verification — regenerate `tree_viewer.html` and run the same kind of Node-based logic verification against the real embedded dataset used for 002 (no automated JS test harness exists in this project)

**Target Platform**: Same generated static HTML page as 002

**Project Type**: Single generated-artifact web page

**Performance Goals**: N/A — row count grows modestly (verified on real data: 490 labels → 525 positions, i.e. ~7% more rows before the 002 color split is applied on top)

**Constraints**: Must not regress Feature 002 (color split stays; new row key is `position_key|color`, not a reversion to `eco|name|color`); must not change `tree.sqlite`/`tree_engine.py` (that data feeds the separate Opening Tree tab and is untouched); per data-verified research, must not change what counts as "the same position" from what `_annotate_game_opening()`/`eco_lookup` already use (no new position-equality definition)

**Scale/Scope**: `tree_viz.py`: one new field in `load_pgns()` (Python) plus the same ~10 JS functions already touched by 002, now re-keyed a second time from `eco|name|color` to `position_key|color`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No `.specify/memory/constitution.md` principles are defined for this project — no gates apply.

## Project Structure

### Documentation (this feature)

```text
specs/003-position-node-grouping/
├── plan.md              # This file
├── research.md          # Phase 0 output — includes the real-data verification of the over-merging bug
├── data-model.md         # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet created)
```

No `contracts/` directory — same reasoning as 002 (no external interface).

### Source Code (repository root)

```text
chess-rag/
└── tree_viz.py
    ├── _fen_to_key(fen)              # EXISTING helper — reused, not modified
    ├── load_pgns()                   # Python: add `position_key` field per game
    └── HTML_TEMPLATE (JS)            # Client-side, same functions 002 touched:
        ├── buildOpeningStats()       # key becomes position_key|color; derive positionText
        ├── sortOpenings()            # default direction for 'position' column
        ├── renderOpenings()          # + Position <th>/<td>, sort comparator branch
        ├── openOpModal()             # filter games by position_key (not eco/name text)
        ├── pinCurrentOp() / toggleOpPin() / updatePinnedTabs() / openOpByKey()
        │                             # pin identity becomes position_key + color
        └── renderTogether()          # per-pinned-row game filter by position_key + color
```

**Structure Decision**: Same single-file structure as 002, one additional Python-side field. No new files.

## Complexity Tracking

*No constitution violations — table not needed.*
