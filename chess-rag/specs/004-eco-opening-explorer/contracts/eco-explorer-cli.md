# Contract: `eco_explorer.py` CLI

Mirrors the existing `tree_viz.py` generator's CLI shape (`tree_viz.py:1943` — `--out`, defaulting relative to a base path) so the two scripts feel like one family of tools.

```text
python eco_explorer.py [--eco-cache ./eco_openings.json] [--out ./eco_explorer.html] [--refresh-cache]
```

| Flag | Default | Behavior |
|---|---|---|
| `--eco-cache` | `./eco_openings.json` (repo-root, same file `tree_viz.py` reads/writes) | Path to the FEN-keyed ECO cache. If entries are missing `moves`, the script re-fetches `eco{A-E}.json` from the same upstream URL `tree_viz.py` uses and rewrites this file in place, adding `moves` — existing `eco`/`name` values are preserved untouched. |
| `--out` | `./eco_explorer.html` | Output path for the generated static page. |
| `--refresh-cache` | off | Force re-fetching upstream data and rewriting `--eco-cache` even if `moves` is already present on every entry (for picking up upstream corrections). |

**Exit behavior**: Non-zero exit + message to stderr if the cache can't be read/written or if upstream fetch fails *and* no usable local cache exists (mirrors `tree_viz.py`'s existing `[warn]`-and-continue behavior when `requests` is unavailable, at `tree_viz.py:171-173` — the explorer can still generate a page from whatever cache is on disk, just without newly-added `moves`).

**Idempotency**: Running with no flags twice in a row produces byte-identical `eco_explorer.html` output given an unchanged cache (no timestamps or non-deterministic ordering baked into the template), consistent with `tree_viz.py`'s existing generation model.
