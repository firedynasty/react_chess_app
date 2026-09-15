# Phase 1 Data Model: Opening Color Column

No persisted schema changes. This documents the in-memory shapes touched in the generated page's embedded JS (`tree_viz.py`'s `HTML_TEMPLATE`).

## Opening Stats Row (client-side, `buildOpeningStats()` output)

| Field   | Type   | Notes |
|---------|--------|-------|
| `eco`   | string | Unchanged — from `g.eco` |
| `name`  | string | Unchanged — from `g.opening` |
| `color` | string | **New.** `'white'` or `'black'`, from `g.my_color`. Now part of the row's grouping key alongside `eco`+`name`. |
| `w`     | number | Unchanged semantics — wins, now scoped to `color` |
| `d`     | number | Unchanged semantics — draws, now scoped to `color` |
| `l`     | number | Unchanged semantics — losses, now scoped to `color` |

**Key**: previously `` `${eco}|${name}` ``, becomes `` `${eco}|${name}|${color}` `` everywhere a row's identity is used (pin membership, modal lookup, `_currentOpKey`).

## Pinned Opening (`_pinnedOps` entries)

| Field   | Type   | Notes |
|---------|--------|-------|
| `eco`   | string | Unchanged |
| `name`  | string | Unchanged |
| `color` | string | **New.** Pinning is now per (opening, color) row, consistent with the row identity above. |

## Source data (unchanged)

`PGNS[id].my_color` (`'white'` \| `'black'`) already exists per game (Python `load_pgns()`, from the PGN's `MyColor` header written by `ingest.py`) — no new data collection, no change to `load_pgns()` or the embedded `PGNS` object's shape.

## State transitions

None — this is a stateless recomputation on every render (`renderOpenings()`), driven by the existing filter state (date range, time control, name search) plus the new implicit color split. No persistence of UI state across page loads beyond what already exists (`_pinnedOps` is in-memory only today).
