# Chess-RAG Pipeline

Per-user "buckets" under `chess-rag/data/<username>/`. Each bucket is
self-contained: raw annotated PGNs, merged `games.pgn`, `state.json`,
`tree.sqlite`, `tree_viewer.html`, `reports/`, and copies of the four
pipeline scripts.

```
chess-rag/
├── ingest.py  tree_engine.py  tree_viz.py  report.py   ← master copies
└── data/
    └── tttstanley/              ← a bucket (everything below lives inside)
        ├── ingest.py  tree_engine.py  tree_viz.py  report.py
        ├── raw/chesscom/*.pgn   ← one annotated PGN per game
        ├── games.pgn  state.json  tree.sqlite
        ├── tree_viewer.html
        └── reports/<run>/report.html
```

---

## Replenish an existing bucket

From inside the bucket — everything is no-args:

```bash
cd chess-rag/data/tttstanley
python ingest.py          # fetch games newer than state.json + auto-annotate (~5s each)
python tree_engine.py     # rebuild tree.sqlite
python tree_viz.py        # regenerate tree_viewer.html
```

Or from `chess-rag/` root (case doesn't matter — the key is lowercased):

```bash
python ingest.py TTTStanley
python tree_engine.py tttstanley
python tree_viz.py tttstanley
```

Generate AI reports (needs `OPENAI_API_KEY`):

```bash
cd data/tttstanley
python report.py --position "d4 d5 e3 Nc6"     # or: python report.py <game_id> [game_id...]
```

> Caveat: `tree_engine.py` only *adds* edges. If ingest trimmed old games,
> their edges linger in `tree.sqlite`. For a tree that exactly matches the
> current store: `rm tree.sqlite` before rebuilding (takes ~5s).

---

## New username

```bash
cd chess-rag
python ingest.py NewName        # creates data/newname/: fetches 100 games,
                                # annotates with Stockfish, copies the 4 scripts in
cd data/newname
python tree_engine.py           # build tree.sqlite
python tree_viz.py              # generate tree_viewer.html
```

---

## Hand off to a friend

```bash
zip -r newname.zip chess-rag/data/newname     # or just copy the folder
```

The friend opens `tree_viewer.html` and any `reports/*/report.html` in a
browser. Nothing to install, no API key needed — they can browse the tree,
replay games with the Stockfish lines, flip boards. They cannot *generate*
new reports (that needs your `OPENAI_API_KEY`).

---

## What ingest.py does

1. Walks Chess.com archives newest → oldest until `--max` games collected
   (incremental on later runs via `state.json → last_fetched_at`)
2. Writes one PGN per game to `raw/chesscom/<game_id>.pgn` with extra
   headers (`MyColor`, `MyResult`, `OpponentUsername`, …)
3. **Annotates each new PGN with local Stockfish** (depth `--depth`,
   default 15): `?!` / `?` / `??` glyphs, best-line `( … )` variations,
   `[%eval ±x.xx]` comments. Annotated files carry an
   `[EngineAnalysis]` header so they are never re-analyzed
4. Rebuilds `games.pgn` (newest first, capped at `--max`) and trims old raws
5. Syncs the four pipeline scripts into the bucket

## Useful flags

| Flag | Effect |
|---|---|
| `ingest.py --max 200` | Keep a larger game store |
| `ingest.py --depth 18` | Deeper Stockfish analysis (slower) |
| `ingest.py --no-analyze` | Skip Stockfish (fast fetch) |
| `ingest.py --analyze-all` | Backfill annotation on existing PGNs |
| `report.py --model gpt-4o-mini` | Cheaper reports |

## Requirements

- `pip install -r requirements.txt` (requests, python-chess, openai)
- `stockfish` binary (`brew install stockfish`) — for annotation
- `export OPENAI_API_KEY=sk-...` — only for `report.py`
