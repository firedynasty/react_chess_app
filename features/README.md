# Feature inventory

`index.html` is 19,242 lines with **280 buttons** and **25 `…Modal` overlays**
(`grep -c 'id="[^"]*[Mm]odal"'`). This directory maps every
button to the feature that owns it, so a cut is a lookup instead of a hunt.

- **[BUTTONS.md](BUTTONS.md)** — all 280 buttons, sorted by line, each linked to its feature file.
  Generated. Rerun `python3 features/extract_buttons.py` after every edit; line numbers move.
- **`NN-<feature>.md`** — one file per feature: its buttons, its API endpoints, its localStorage
  keys, its other files, and a keep/cut verdict. Hand-written. These are yours to argue with.
- **[duplicate-controls.md](duplicate-controls.md)** and **[clipboard-sprawl.md](clipboard-sprawl.md)**
  — the two problems that cut across every feature.
- **[HISTORY.md](HISTORY.md)** — what git history says about each feature: commits, share of all
  work, first and last touch, days idle, and what has already been removed. Generated.
- **`extract_buttons.py`** — rebuilds `BUTTONS.md`, traces one button before you delete it
  (`--trace <id>`), and syntax-checks every inline `<script>` (`--check`). `--help` for all of it.
  This copy is chess-wired and stays here; the portable version of the same tool is
  `~/Documents/technical/claude_skills/list_features/buttons.py`, which reproduces this folder's
  inventory line for line from its own rules file. Use it on *other* repos:
  ```bash
  python3 ~/Documents/technical/claude_skills/list_features/buttons.py --repo ~/code/thing --scaffold
  ```
- **`HISTORY.md` is rebuilt from outside the repo too** — `~/Documents/technical/claude_skills/list_history/`,
  with the chess grouping in its `rules/react-chess-analysis.json`:
  ```bash
  python3 ~/Documents/technical/claude_skills/list_history/history.py \
      --rules react-chess-analysis.json \
      --target index.html --link-dir features -o features/HISTORY.md
  ```
- `google-drive-sheets-loader.html` — pre-existing extract, not part of the inventory.

## Two measurements, read together

`extract_buttons.py` measures **surface** — what a feature is today. `history.py` measures
**attention** — what you keep coming back to. Neither alone is a verdict:

| | high attention | low attention |
|---|---|---|
| **big surface** | keep, maybe trim | **cut first** |
| **small surface** | keep | cut quietly |

Where the two disagree with the verdicts in this folder, [HISTORY.md](HISTORY.md) wins, because
commits are evidence of what you actually use and my verdicts were read off the code.

## The actual problem

Not feature count. **Duplicate paths to four jobs:**

| Job | Entry points today |
|---|---|
| Get a game onto the board | ~9 → ~5 (four went with [03](03-supabase-games.md)) |
| Attach a variation to a move | 8 |
| Get a line out as text | 39 buttons, 29 `clipboard.writeText` calls |
| Print study cards | 8 |

## Verdicts

| # | Feature | Buttons | Verdict |
|---|---|---:|---|
| 01 | [Core board + move navigation](01-core-board.md) | 22 | KEEP |
| 02 | [chess.com / Lichess fetchers](02-game-sources.md) | 3 | CUT (keep one) |
| 03 | [Supabase game library](03-supabase-games.md) | — | **REMOVED** |
| 04 | [Supabase Lines pane](04-supabase-lines.md) | 20 | KEEP |
| 05 | [Transfer to puzzles](05-puzzles-transfer.md) | 4 | KEEP |
| 06 | [Save → Puzzles](06-puzzles-save.md) | 3 | MERGE into 05 |
| 07 | [Variation adders](07-variations.md) | 34 | CUT — keep 2 of 8 |
| 08 | [Practice](08-practice.md) | 15 | KEEP, trim copy row |
| 09 | [What went wrong](09-what-went-wrong.md) | 21 | KEEP |
| 10 | [Mistake hop](10-mistake-hop.md) | 3 | KEEP |
| 11 | [Move comments + bubbles](11-move-comment.md) | 10 | KEEP |
| 12 | [Print list + Print Line](12-print-cards.md) | 27 | MERGE two modals into one |
| 13 | [PGN Library sidebar](13-pgn-library.md) | 7 | CUT |
| 14 | [Google Sheets + Drive](14-sheets-drive.md) | 22 | CUT the write/table half |
| 15 | [Dropbox](15-dropbox.md) | — | **REMOVED** |
| 16 | [Coach Chat + AI → PGN](16-coach-ai.md) | 21 | KEEP, cut the extra buttons |
| 17 | [Study tool: board2 + report](17-study-tool-report.md) | 39 | CUT most of it |
| 18 | [FEN export / queue / images](18-fen-export.md) | 16 | CUT the queue |
| 19 | [Type/Play + vs Stockfish](19-typed-move.md) | 10 | KEEP |
| 20 | [View Text modal](20-text-view.md) | 3 | MERGE into clipboard work |

Ten keeps, eight cuts or merges, two done. The keeps are, with one exception, everything you built
in the last three months.

## Cut order

Risk rises as you go down. Stop whenever you like — every step stands on its own.

1. **[duplicate-controls.md](duplicate-controls.md)** — 8 provably dead `display:none` buttons
   (nothing in the file ever reveals them) and 7 buttons whose only job is clicking another
   visible button. Zero UI change, zero risk. Six of the eight belong to step 2.
   *Started:* `#loadToBoard` is gone (`#loadToBoardMini` keeps the paste → board workflow), and
   all 11 Dropbox buttons went with [15-dropbox.md](15-dropbox.md), three of them hidden-but-live.
   The four `#pzPgnSection` buttons misfiled under [06](06-puzzles-save.md) are gone too, and the
   **load selected** and **📋 copy url** pairs went with [03](03-supabase-games.md).
2. **[17-study-tool-report.md](17-study-tool-report.md)** — the report half. Largest family,
   oldest code, six of its buttons already hidden. Leave `board2*` alone; that IS the main board.
3. **[03-supabase-games.md](03-supabase-games.md)** — **done.** `/api/games`, `/api/staging` and
   `/api/game-report` are gone, with 17 buttons, two localStorage keys (`sbReportAccessCode` was
   never this feature's alone and stayed), the whole `?game_id=` deep link, and 1,128 lines of
   `index.html`. The file is now the record of what it cost.
4. **[clipboard-sprawl.md](clipboard-sprawl.md)** — 41 buttons down to three functions. Cannot
   touch the move tree, so it is safe; biggest visible-clutter win per line changed.
5. **[13-pgn-library.md](13-pgn-library.md)**, **[18-fen-export.md](18-fen-export.md)** (queue only),
   **[14-sheets-drive.md](14-sheets-drive.md)** (write mode, then the table) — independent, small.
6. **[12-print-cards.md](12-print-cards.md)**, **[06-puzzles-save.md](06-puzzles-save.md)**,
   **[20-text-view.md](20-text-view.md)** — merges, so they need a decision per button, not a delete.
7. **[07-variations.md](07-variations.md)** — last. Most entangled with the move tree.

## Culling one button

**Work from the id, never the line number.** Ids are stable; line numbers shift the moment you
delete anything above them. `BUTTONS.md` is for finding the id — not for copying line numbers out of.

```bash
python3 features/extract_buttons.py --trace loadToBoardMini
```

That prints the blast radius: the element, the click binding (including the
`const btn = getElementById(...)` alias form), the handler and **whether anything else calls it**,
any `window.` export, and whether the element is read by id somewhere that would go `null` after
the delete. It ends with a `CANDIDATE LINES TO DELETE` list, plus `!!` warnings when that list is
not safe as it stands. A button id or any piece of its label both work.

Then:

```bash
# 2. delete only what the trace accounted for
# 3. verify every inline <script> still parses
python3 features/extract_buttons.py --check
# 4. refresh the inventory -- the line numbers have all moved
python3 features/extract_buttons.py
# 5. record it under "## Culled" in the owning features/NN-*.md, then commit
```

One feature per commit, named for the feature.

### The three traps the trace exists to catch

1. **The handler is shared.** `updateReportBtn` is a dead hidden button, but its handler
   `updateReportWithPgn()` has eight other callers. Delete the button, keep the function.
2. **The handler reads its own button by id.** `updateReportWithPgn` does
   `const btn = document.getElementById('updateReportBtn'); btn.textContent = 'Updated!'`,
   unguarded. Delete only the element and that line throws on the next move. The trace flags every
   id read that is not the click binding.
3. **`display:none` is not dead.** Two hidden buttons are revealed by JS once reports load (three
   more were, until Dropbox went). The trace prints `REVEALED by JS at [...]` versus `reveal never`.

A worked example, start to finish, is in [01-core-board.md](01-core-board.md) under `## Culled`.

## How to cut safely

One feature per commit, named for the feature, so `git revert <sha>` puts it back whole.
**Git is the archive** — that is what `removed_features/` and `hidden-features/` were trying to be,
and they can go.

After each cut:

```bash
python3 features/extract_buttons.py     # line numbers moved; also catches orphaned handlers
```

Then run your inline-script strict check. A 21k-line single file punishes batching: commit
`db57b4e` is the time modal HTML, script and `window` exports landed in three different scopes and
the button silently did nothing.

Two traps the inventory already knows about:

- Deleting a button is not deleting a feature. Its handler, its modal `<div>`, its
  `window.x = x` export and its localStorage key all live elsewhere in the file. Each feature file
  lists them.
- Some buttons are the only caller of a function another feature also needs, so check for a
  second caller before deleting a handler — but check which way the dependency runs.
  `sbCopyGameLink` was the worked example: the mini bar's `📋 Copy URL` called it, so the plan was
  to move it out before cutting [03-supabase-games.md](03-supabase-games.md). The trace showed the
  opposite. The only writer of `window.supabaseLoadedGame` was *inside* the cut, so the mini button
  could only ever have reported *"No Supabase game loaded"*, and it went too. A shared **key** can
  still outlive its feature: `sbReportAccessCode` did, and
  [16-coach-ai.md](16-coach-ai.md) owns it now.

## Non-feature cleanup

Free, unrelated to any button:

- `src/` is **251 MB on disk; 7.3 MB is served.** Only `src/stockfish-17.1-lite-single-03e3232.js`
  and its `.wasm` are loaded (`index.html:3339`, `index.html:3484`). The other variants are
  gitignored but still local — `rm` them.
- Root `stockfish.js` (1.5 MB) is referenced by nothing.
- `react-chat-report-viewer/` (107 tracked files) and `preloaded_reports/` (23) are not loaded by
  `index.html` at all. Your `vercel.json` `excludeFiles` list names ten such directories — that
  list is the inventory of what you already know is dead.
- ~25 loose `.txt`/`.md` notes in the repo root (`summary0202.txt`, `fordelete.sh`, `output.txt`,
  `011726.txt`, …).
- `src/*.cpp` — the full Stockfish C++ tree is tracked but never compiled (`buildCommand` is
  empty). Keep only if `stockfish-implementation/research-stockfish-nnue.md` is still live work.

`api/lichess.py` looks orphaned — nothing references it — but its header says it is parked
deliberately until the upstream Lichess bulk endpoint stops 404ing. Leave it.
