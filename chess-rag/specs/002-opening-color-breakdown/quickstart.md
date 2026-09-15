# Quickstart: Validating Opening Color Column

## Prerequisites

- A bucket under `data/<key>/` with `games.pgn` containing at least:
  - One opening played only as White
  - One opening played only as Black
  - One opening (same ECO + name) played as both White and Black

## Regenerate the viewer

```bash
cd chess-rag
python tree_viz.py <key>     # or the project's existing invocation for tree_viz.py
```

This regenerates `data/<key>/tree_viewer.html` from the current `HTML_TEMPLATE`.

## Validation scenarios

1. **Single-color rows unaffected**
   Open `data/<key>/tree_viewer.html` → "Openings Stats" tab. Find the White-only and Black-only openings. Confirm each shows exactly one row with a clear color indicator (SC-001, User Story 1 / Acceptance Scenarios 1–2).

2. **Mixed opening splits into two rows**
   Find the opening played as both colors. Confirm it now appears as two rows — one White, one Black — each with its own Games/W-D-L/Win% independent of the other, and that the two rows' game counts sum to what was previously shown as one combined row (SC-002, User Story 1 / Acceptance Scenario 3).

3. **Color column sorts like the others**
   Click the Color column header. Confirm all White rows group together, all Black rows group together (order reversed on a second click). Click a different header (e.g. Win%) afterward and confirm normal single-column sort resumes (SC-003, User Story 2).

4. **Detail modal respects the row's color**
   Click into the mixed opening's White row. Confirm only White games are listed. Repeat for the Black row — confirm only Black games are listed (FR-005, Edge Cases).

5. **Pinning is per-color**
   Pin the White row for the mixed opening. Confirm the pinned nav tab and the "Together" view reflect only the White games for that opening, not the Black ones (Edge Cases, data-model.md Pinned Opening).

6. **Existing filters still combine correctly**
   Apply a date-range or time-control filter that excludes some of the mixed opening's games. Confirm both the White and Black rows recompute to reflect only the filtered games (FR-006).

## Expected outcome

All six scenarios pass with no regression to the table's existing behavior (search-by-name, date/time-control filters, pin/unpin, "Together" combined view) for openings that were never mixed-color to begin with.
