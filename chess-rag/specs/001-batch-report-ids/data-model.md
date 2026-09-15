# Phase 1 Data Model: Batch Game ID Copy for Report Comparisons

This feature introduces no persisted data and no new entities — it operates entirely on in-memory/DOM state that already exists in `tree_viewer.html`. Documented here for completeness against the spec's Key Entities section.

## Game (existing, unchanged)

Already represented by the in-memory `PGNS` object (keyed by game ID) populated from the bucket's data. Relevant fields used by this feature:

| Field | Type | Used for |
|---|---|---|
| `id` | string | The value copied by the new actions |
| `white`, `black` | string | Not used by copy actions (display only) |
| `pgn` | string | Not used by copy actions (used by the existing PGN-copy actions) |

No new fields required.

## Selection (existing, unchanged)

Represented by the `checked` state of `.game-chk` checkboxes already rendered per row (`tree_viewer.html:708`). `selectedIds()` (line 762) already reads this into an array. No new state needed — "copy selected IDs" reads the same DOM state "copy selected PGN(s)" already reads.

## Copied ID List (new, transient — clipboard content only, not stored)

Not a persisted entity; exists only as the string written to the OS clipboard.

| Property | Rule |
|---|---|
| Format | Game IDs joined by a single space (`' '`) |
| Ordering | Same order as the source list (`gamesAtPosition(...)` order for "all"; DOM order of checked `.game-chk` elements for "selected") |
| Duplicates | Removed — de-duplicate the ID array (e.g. via a `Set`) before joining, per spec FR-004 |
| Content | IDs only — no PGN text, no labels, no surrounding whitespace/newlines beyond the single-space separator |

## Comparison Report (existing, unchanged — produced by `report.py`, out of scope for this feature)

Documented for traceability to spec's Key Entities section only:

| Field | Source |
|---|---|
| `run_meta.json` | `report.py` main(), line 381 |
| `<game_id>.md` per game | `report.py` main(), line 420 |
| `comparison.md` | `report.py` main(), line 438 — generated only when `len(games) >= 2` |

This feature does not modify how these are produced; it only makes it faster to arrive at a valid `game_ids` input for them.
