# Phase 0 Research: Batch Game ID Copy for Report Comparisons

No `[NEEDS CLARIFICATION]` markers remained in the spec, so this phase confirms the existing-code facts the plan relies on rather than resolving open unknowns.

## Decision: Reuse the existing per-row/toolbar copy pattern, add two sibling actions

**Decision**: Add `copyAllIds()` and `copySelectedIds()` functions plus two buttons ("Copy all ID(s)", "Copy selected ID(s)") to the `#games-toolbar` in `tree_viewer.html`, directly alongside the existing `copyAll()` ("Copy all PGN(s)") and `copySelected()` ("Copy selected PGN(s)") buttons.

**Rationale**: Confirmed by reading `data/tttstanley/tree_viewer.html`:
- `#games-toolbar` (line 391) already holds a "Select all" checkbox and a "Copy selected PGN(s)" button; a separate "Copy all PGN(s)" button (line 394) sits next to it.
- `selectedIds()` (line 762) already returns `[...document.querySelectorAll('.game-chk:checked')].map(el => el.dataset.id)` — the exact list needed for "copy selected IDs", just not currently joined into a copyable string on its own.
- `gamesAtPosition(currentKey, true)` (used at line 774 inside `copyAll()`) already returns the full ordered ID list for the active position — the exact list needed for "copy all IDs".
- Both new functions are therefore thin wrappers: reuse `selectedIds()` / `gamesAtPosition(currentKey, true)`, dedupe, join with `' '`, write to clipboard, and reuse the existing `alert(...)` confirmation pattern from `copySelected()`/`copyAll()` (lines 766-777).

**Alternatives considered**:
- *Repurpose the existing "Copy ID" per-row button to build a running multi-ID list* — rejected: `copyId()` (line 727) already has different semantics (append to whatever's on the clipboard, single ID at a time, used for ad-hoc note-taking); changing it risks breaking that existing single-game workflow, and it doesn't give an atomic "all" or "selected" action.
- *Copy a full ready-to-run shell command (`python report.py <ids>`)* — rejected per spec Assumptions: `--key`/`--position` usage varies by how the user runs the script (from inside the bucket vs. with `--key`), so a hardcoded command prefix would often need editing anyway; bare IDs are the more universally correct primitive matching `report.py`'s `game_ids` positional `nargs="*"` argument (report.py:326).
- *Introduce a "Run report" action that shells out from the browser* — rejected: `tree_viewer.html` is a static file with no backend process; there is no mechanism in this project for a browser page to invoke a local Python script, and adding one would be a much larger, out-of-scope change (would need a local server component). The spec's Assumptions section already documents that the user runs `report.py` themselves after copying.

## Decision: No changes needed to `report.py`

**Decision**: `report.py` is left untouched.

**Rationale**: Confirmed by reading `data/tttstanley/report.py` lines 322-450: it already accepts `game_ids` as positional CLI arguments (`nargs="*"`, line 326), and already generates a `comparison.md` whenever `len(games) >= 2` (line 432), built from `build_comparison_prompt()` (line 268) which explicitly compares games and is what the user's example output format (wins vs. losses, opening deviations) already comes from. The feature gap is purely "how do I get IDs out of the viewer efficiently," not "does the report tool compare games" — it already does.

**Alternatives considered**: None — this was verified directly against the source rather than inferred, so no alternative approaches were needed for this decision.
