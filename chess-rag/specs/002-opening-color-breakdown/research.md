# Phase 0 Research: Opening Color Column

No open technical unknowns — this is a scoped change to existing, already-read code (`tree_viz.py`'s `HTML_TEMPLATE`). Decisions below record the choices made while translating the spec into an implementation approach.

## Decision: Row key becomes `eco|name|color`

**Rationale**: The table already keys rows by a string (`r.eco + '|' + r.name`) used for pin identity (`_currentOpKey`), pin membership checks, and modal lookups. Appending `|` + `my_color` is the minimal change that makes every existing key-based lookup color-aware without redesigning the identity scheme.

**Alternatives considered**: A separate `color` field alongside an unchanged `eco|name` key, with color-aware comparisons done via multi-field checks everywhere. Rejected — every one of the ~10 call sites already does simple string/field equality against the combined key or the `{eco, name}` pair; keeping a single composite key (now 3-part) is less code than converting every comparison to a 3-field match.

## Decision: Color displayed as a short label/icon, not spelled out

**Rationale**: Table is already dense (7 columns); "White"/"Black" text would widen the Opening/ECO columns unnecessarily. A compact glyph (e.g. "♔ White" / "♚ Black", or a colored dot + short text) matches the visual density of the existing `eco-badge` styling.

**Alternatives considered**: Full-word column with no icon — simpler but visually noisier next to the existing compact badges. Deferred to implementation styling; either satisfies FR-002/FR-003, exact styling is not a spec-level concern.

## Decision: No Python-side (`tree_viz.py` generator, non-template) changes needed

**Rationale**: `load_pgns()` already emits `my_color` per game (`"my_color": _pgn_header(text, "MyColor")`). The color split is pure aggregation logic that already lives in client-side JS (`buildOpeningStats()`), operating over the already-embedded `PGNS` object. No new PGN header, no schema change, no regeneration-time behavior change.

**Alternatives considered**: Pre-aggregating color-split rows in Python and embedding them alongside `PGNS`. Rejected as unnecessary duplication — the JS already recomputes stats from `PGNS` on every filter change (date range, time control, name search), and color is just one more grouping field in that existing recomputation.

## Decision: "Games" count and W/D/L semantics unchanged, just scoped per color

**Rationale**: Spec FR-001/SC-002 require each (opening, color) row's numbers to be self-consistent and to sum to the opening's prior combined total — this falls out naturally from filtering `PGNS` entries by `g.my_color` before aggregating, with no new counting logic needed beyond the existing win/draw/loss classification already in `buildOpeningStats()`.
