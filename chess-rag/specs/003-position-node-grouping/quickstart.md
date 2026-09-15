# Quickstart: Validating Position Column and Transposition Merging

## Prerequisites

- Feature 002 (Opening Color Column) already implemented — this feature builds on it.
- A bucket under `data/<key>/` with real games; `data/jyan_500` (1499 games) is known-good for this, including at least one coarse opening label spanning multiple distinct positions (e.g. "Queen's Pawn: London" in that dataset spans 7 positions — good for scenario 2).

## Regenerate the viewer

```bash
cd chess-rag
python3 tree_viz.py <key>
```

## Validation scenarios

1. **Position column visible and sortable**
   Open the Openings Stats tab. Confirm every row shows a move-sequence Position value. Click the Position header — rows re-sort by that text; click again to reverse. Confirm rows sharing a common prefix (e.g. two "e4 e5..." rows) land next to each other after sorting (User Story 1).

2. **Over-merged label splits into precise rows**
   Find a label that previously spanned multiple positions (e.g. search "London" in the dataset noted above). Confirm it now appears as multiple rows — one per distinct exact position — instead of one row combining all of them, and that the combined game count across the split rows equals what was previously shown as one row's total (SC-001, User Story 2).

3. **True transpositions still merge**
   Identify (or construct in a small test PGN) two games that reach an identical resulting position via different move orders. Confirm they appear as one row with a combined game count and W/D/L (SC-001, User Story 2 Acceptance Scenario 1).

4. **Detail view lists all contributing games regardless of move order**
   Open a merged row's detail view (from scenario 3, if available). Confirm every contributing game is listed, even the one whose own move sequence differs from the row's displayed Position (User Story 2 Acceptance Scenario 2).

5. **Search matches position text too**
   Type a move-sequence fragment (e.g. "e4 e5") into the existing openings search box. Confirm rows whose Position contains that fragment appear, in addition to any name-matches (User Story 3).

6. **Feature 002 still works**
   Confirm rows are still split by color (an opening played as both colors is still two rows), the Color column still sorts, and pinning/the Together view still work — now keyed by position instead of by opening label, but otherwise behaviorally consistent with 002's quickstart scenarios.

## Expected outcome

All six scenarios pass. Total row count should increase modestly relative to Feature 002 alone (in the verified real dataset, roughly +35 rows from label-to-position splitting, before doubling effects from any newly-mixed-color positions), with no games lost or double-counted — the sum of every row's game count must equal the bucket's total game count.
