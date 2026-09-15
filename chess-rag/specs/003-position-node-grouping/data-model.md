# Phase 1 Data Model: Position Column and Transposition Merging

## `PGNS[id]` (Python `load_pgns()` output — one new field)

| Field          | Type          | Notes |
|----------------|---------------|-------|
| `position_key` | string \| null | **New.** `_fen_to_key(opening_fen)` — the existing 4-field-FEN normalization already used to join against `eco_lookup`. `null` when `opening_fen` is empty (no ECO match; 5 of 1499 games in the verified dataset). |

All other fields (`eco`, `name`, `opening_moves`, `opening_fen`, `my_color`, etc.) are unchanged from today.

## Opening Stats Row (client-side, `buildOpeningStats()` output)

| Field         | Type   | Notes |
|---------------|--------|-------|
| `positionKey` | string | **New.** Grouping key component, from `g.position_key` (or a fixed sentinel string for the null/no-match bucket, so those games still group together as they do today). |
| `positionText`| string | **New.** Display/sort value for the Position column — the most common `opening_moves.join(' ')` among the row's contributing games (same tie-break already used in `openOpModal()`'s move-sequence display). |
| `eco`         | string | Unchanged — read from any one contributing game (proven a pure function of `positionKey` on real data; see research.md) |
| `name`        | string | Unchanged — same as `eco` |
| `color`       | string | From Feature 002 — unchanged |
| `w`/`d`/`l`   | number | Unchanged semantics, now scoped to `positionKey` + `color` |

**Key**: `` `${positionKey}|${color}` `` — replaces 002's `` `${eco}|${name}|${color}` `` as the row identity used for pin membership, modal lookup, and `_currentOpKey`. `eco`/`name` remain on the row purely as display fields, no longer part of the identity.

## Pinned Opening (`_pinnedOps` entries)

| Field         | Type   | Notes |
|---------------|--------|-------|
| `positionKey` | string | **New.** Identity component, replacing the `eco`+`name` pairing used for equality in Feature 002. |
| `color`       | string | Unchanged — still part of identity |
| `eco`         | string | Display only |
| `name`        | string | Display only |
| `positionText`| string | **New.** Display only — shown alongside eco/name in pinned tabs and the Together view so a pinned row remains identifiable even if two different positions happen to render the same opening name text (not observed in real data, but the display field costs nothing and removes the theoretical ambiguity). |

## Relationship to `tree.sqlite` / `tree_engine.py`

No relationship change: `position_key`'s 4-field-FEN normalization is the same convention `tree_engine.py`'s `_position_key()` uses for the separate Opening Tree tab's `positions`/`edges` tables, but this feature does not read from or write to `tree.sqlite` — it only reuses the existing `_fen_to_key()` helper already present in `tree_viz.py` for ECO matching.

## State transitions

None — same as Feature 002, a stateless recomputation on every `renderOpenings()` call driven by existing filter state plus the new grouping key.
