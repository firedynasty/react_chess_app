# Quickstart: Validate Batch Game ID Copy

Prerequisites:
- `data/tttstanley/tree_viewer.html` updated per this feature (`copyAllIds()`/`copySelectedIds()` + buttons added).
- A browser with clipboard-write permission for local files (or the page served over `http://localhost`).
- `OPENAI_API_KEY` set, and `openai` + `python-chess` installed, only if you go on to run `report.py` in step 4.

## 1. Copy all IDs at a position (User Story 1)

1. Open `data/tttstanley/tree_viewer.html` in a browser.
2. Navigate to any opening/tree position that has 2+ games listed.
3. Click **Copy all ID(s)**.
4. Paste into a text editor.

**Expected**: A single line of space-separated game IDs, one per listed game, no duplicates, no PGN text — matching the count of games shown.

## 2. Copy only selected IDs (User Story 2)

1. From the same game list, check 2 of the listed games.
2. Click **Copy selected ID(s)**.
3. Paste into a text editor.

**Expected**: Exactly the 2 checked games' IDs, space-separated.

4. Uncheck all games, click **Copy selected ID(s)** again.

**Expected**: A message tells you nothing is selected; the clipboard still contains the 2 IDs from step 2/3 (unchanged).

## 3. Duplicate-safety edge case

1. Find or construct a view where the same game ID could appear twice in the visible list (e.g. a pinned opening plus the same game reachable from the main tree, if the UI ever merges such views).
2. Click **Copy all ID(s)**.

**Expected**: The ID appears only once in the pasted output.

## 4. End-to-end: run the existing report generator (User Story 3)

From inside `data/tttstanley/`:

```bash
python report.py <paste the copied IDs here>
```

**Expected**:
- Console prints one line per game plus `Generating comparison report...` (only when 2+ valid IDs were pasted).
- A new folder appears under `data/tttstanley/reports/` containing `run_meta.json`, one `<id>.md` per game, and (for 2+ games) `comparison.md`.
- Open `comparison.md` and confirm it names each game's result (win/loss) and includes a section discussing differences/similarities between the wins and losses in the batch — this is pre-existing `report.py` behavior (see `research.md`), so this step validates the copied ID format was accepted with zero manual edits, per spec SC-002.

## Out of scope for this validation

- `data/jyan_500/tree_viewer.html` and `against_computer/tree_viewer.html` are untouched — no need to re-test them.
- No changes to `report.py`'s prompt content or comparison logic — this quickstart does not evaluate report *quality*, only that the copy → paste → run path works end-to-end.
