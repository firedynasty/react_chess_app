# Contract: `eco_openings.json` schema (augmented) & embedded page data

This isn't a network API — the "contract" is the on-disk cache format and the JSON literal `eco_explorer.py` bakes into `eco_explorer.html`. Both existing readers (`tree_viz.py`, `lichess_tree_viz.py`) and the new generator depend on this shape staying stable.

## `chess-rag/eco_openings.json` (on disk, FEN-keyed dict)

```json
{
  "<4-field FEN>": {
    "eco": "B10",
    "name": "Caro-Kann Defense",
    "moves": ["e4", "c6"]
  },
  "...": { "eco": "A00", "name": "Amar Gambit" }
}
```

- `eco`, `name`: **unchanged** from the current format — existing consumers (`tree_viz.py:159-192`, `lichess_tree_viz.py`, `push_to_supabase.py`) keep reading exactly these two fields and must not break.
- `moves`: **new**, optional. SAN move array from the game start to this FEN. Absent on entries where the upstream source has no move string for that position (data gap — see data-model.md).

Backward compatibility: any existing reader that does `entry.get("eco")` / `entry.get("name")` and ignores unknown keys is unaffected by the new `moves` field. No reader currently does strict schema/key validation on this file.

## Embedded page data (`eco_explorer.html`, `const ECO_LINES = __ECO_LINES_JSON__;`)

```json
[
  {
    "eco": "B10",
    "name": "Caro-Kann Defense",
    "moves": ["e4", "c6"],
    "fen": "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -"
  }
]
```

Array form (not FEN-keyed) — the page needs to iterate/sort/filter the full set, and `fen` moves from being the dict key to an explicit field so array order can be whatever the generator chooses (grouped by code, for a smaller diff-friendly output).

- Lines with no `moves` are still included (`"moves": []`) so counts (FR-007) reflect the true total and the UI can render the "unavailable" state (FR-008) rather than silently dropping them.
- `volume` is intentionally **not** included per-line — it's `eco[0]`, computed once client-side, to avoid redundant bytes across ~12,000 entries.

## `eco_explorer.py` CLI

See `eco-explorer-cli.md` for the generator's command-line contract.
