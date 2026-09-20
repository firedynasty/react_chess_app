# Phase 1 Data Model: ECO Opening Explorer

## Entities

### Opening Line

A single named entry in the ECO classification (spec Key Entities). One record per FEN key in the augmented `eco_openings.json`.

| Field | Type | Source | Notes |
|---|---|---|---|
| `fen` | string (4-field, no halfmove/fullmove counters) | dict key in `eco_openings.json` | Existing key format (`_fen_to_key()`, `tree_viz.py:154-156`) |
| `eco` | string, 3 chars (e.g. `"C20"`) | existing field | Unchanged |
| `name` | string (e.g. `"Sicilian Defense: Najdorf Variation"`) | existing field | Unchanged; may contain a `:`-separated variation/sub-variation per spec |
| `moves` | string\[] (SAN, e.g. `["e4","e5","Nf3"]`) | **NEW** — parsed from upstream `moves` string (`"1. e4 e5 2. Nf3"` → strip move numbers) | Absent/empty ⇒ line is a data gap (FR-008); still shown, marked unavailable |
| `volume` | string, 1 char (`"A"`–`"E"`) | derived: `eco[0]` | Not stored — computed at load time (client or generator), since it's a pure function of `eco` |

### ECO Code

Not a separate stored record — a grouping key. `code = eco` (e.g. `"C20"`). All Opening Lines sharing a code are its members; "browse by code" = filter Opening Lines where `eco == code`.

### ECO Volume

Not a separate stored record — `volume = eco[0]`, one of `{A, B, C, D, E}`. "Browse by volume" = filter Opening Lines where `eco[0] == volume`.

### Continuation (not a stored entity)

Not modeled as data — no relationship, edge, or graph is built or stored. "Line B extends Line A" is purely an emergent property of sorting by move sequence (see research.md #4): sorting causes `B` to land immediately after `A` whenever `B.moves` starts with `A.moves`. There is nothing here to persist or compute ahead of time beyond the sort itself.

## Validation / Data-Gap Rules

- A line with `moves == []` (or field absent) still appears in browse/search results (never hidden — per Edge Cases) but is rendered with an explicit "move sequence unavailable" marker instead of a board/move list (FR-008), and sorts into a fixed bucket at the end of the move-sequence sort (since there's no sequence to compare).
- `eco` is always a well-formed 3-character code in the current cache (12,106/12,106 entries observed); no additional validation needed beyond what's already implicitly guaranteed by the upstream source.
- Two lines with identical `moves` but different `fen`/`name` are NOT deduplicated — Edge Cases explicitly requires transposed/near-identical lines to remain distinct entries.

## Derived/In-Memory Structures (generator + client, not persisted)

- `byVolume: Map<char, OpeningLine[]>` — for the volume tab view.
- `byCode: Map<string, OpeningLine[]>` — for the code drill-down view; also the source of the FR-007 "N lines" count.
- `positionOrder: OpeningLine[]` — all lines with non-empty `moves`, sorted by `moves` as a tuple key; lines with empty `moves` appended at the end. Recomputed once at page load, not per-query.
- Search index: none needed beyond `name.toLowerCase().includes(query.toLowerCase())` over the flat line list — dataset size (per research.md) doesn't justify a real inverted index.
