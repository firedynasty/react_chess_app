# Quickstart: ECO Opening Explorer

## Prerequisites

- Python 3.11 with `requirements.txt` installed (`requests`, `python-chess` already present).
- Run from `chess-rag/` (same convention as `tree_viz.py`).

## Generate the page

```bash
cd chess-rag
python eco_explorer.py
open eco_explorer.html   # or double-click it — no server needed
```

First run augments `eco_openings.json` in place with a `moves` field (fetches `eco{A-E}.json` from GitHub if any entries are missing it); subsequent runs reuse the cache.

## Validation scenarios (map to spec Acceptance Scenarios)

1. **Browse by volume/code (US1)** — Select volume "C" → confirm only C00–C99 codes are listed. Select code "C20" → confirm every King's Pawn Game variation (Beyer Gambit, King's Head Opening, Wayward Queen Attack, …) appears, each with its own move sequence. Confirm the line count shown matches the number of rows (FR-007).
2. **Large code stays navigable (Edge Case)** — Pick a 200+-line code (e.g. check current counts via `python -c "import json,collections; d=json.load(open('eco_openings.json')); print(collections.Counter(v['eco'] for v in d.values()).most_common(5))"`) and confirm the list stays scrollable/searchable rather than dumping an unbroken page-length list.
3. **Name search (US2)** — Type "Caro-Kann" into search with no volume/code selected → confirm matches appear from multiple codes (Caro-Kann spans several B-codes) and update as you type. Type a nonsense string → confirm an explicit "no matches" message, not a blank panel.
4. **Line detail + step-through (US3, FR-005)** — Open any line → confirm the board (CSS-grid style matching `against_computer/tree_viewer.html`'s opening-detail modal) renders the final position, the annotated move list is shown (e.g. "1. d4 d5 2. c4 c6"), and Prev/Next (buttons + arrow keys) step the board one ply at a time in both directions.
5. **Sort by move sequence (US1 scenario 4, FR-010, SC-005)** — Switch the list to sort-by-moves and locate the Slav Defense line "d4 d5 c4 c6" (D10) → confirm Queen's Gambit Declined/Semi-Slav lines (longer sequences starting with the same 4 moves, under a different code) appear in the immediately following rows, purely as a result of the sort — no separate "continuations" UI or lookup involved.
6. **Data-gap line (FR-008)** — Find or simulate an entry with no `moves` (e.g. temporarily strip `moves` from one cache entry) → confirm it still appears in its code's list and in search, but is clearly marked as having no playable sequence rather than showing an empty/wrong board.
7. **Distinctness from and independence of played games (FR-006, SC-004)** — Confirm the page never shows W/D/L stats, game lists, copy/reuse-elsewhere controls, or any played-games-derived content, and that browsing/searching always reflects the full ~12,000-line classification regardless of what's in any `data/<account>/` bucket.

## Regenerating after upstream ECO data changes

```bash
python eco_explorer.py --refresh-cache
```
