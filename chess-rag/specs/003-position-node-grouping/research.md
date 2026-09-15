# Phase 0 Research: Position Column and Transposition Merging

## Finding: today's `eco|name` grouping already merges *some* transpositions — the real bug is the opposite direction

Before implementing, I checked the real dataset (`data/jyan_500`, 1499 games, 490 distinct opening labels) to verify the spec's premise. `tree_viz.py`'s `_annotate_game_opening()` already matches each game's opening against the ECO database by **FEN**, at every ply, keeping the deepest match. Since that matching is FEN-driven and order-independent, two games that transpose into the same *named* position (e.g. "e3 e5 d4" vs "d4 e5 e3", if that position is itself cataloged) already get identical `eco`/`name`/`opening_fen` today, and so already land in the same row under the current `eco|name` key.

Querying the real data:

```
Total distinct (eco,name) labels:        490
Total distinct position_keys:             525
Labels mapping to >1 distinct position:    20   (e.g. "D02 Queen's Pawn: London" spans 7 different exact final positions)
Position_keys mapping to >1 distinct label: 0   (name is a pure function of position_key)
```

**Decision**: The actual bug FR-003 fixes is **over-merging**, not under-merging. Today's `eco|name` text label is coarser than the exact resulting position in ~20 cases in this dataset — e.g. every game whose deepest ECO match falls anywhere under "Queen's Pawn: London" gets lumped into one row, even though 7 genuinely different final positions are being averaged together. Re-keying rows by the normalized `position_key` (not the label) makes each row exact, splitting those 20 coarse labels into up to ~35 more precise rows. It does **not** newly merge anything that isn't already merged today, because ECO/name assignment was already FEN-driven.

**Rationale for still doing it as specified**: This matches the spec's Key Entity definition exactly ("Position Node... identified by its normalized position identity") and directly serves User Story 1 (a real Position column, sortable, one row per exact position) even though the User Story 2 framing ("under-counts transpositions") describes a narrower slice of the actual effect. The correctness property in SC-001 ("no position with contributing games from more than one move order is ever shown as two or more separate rows") still holds and is still worth guaranteeing explicitly rather than relying on ECO-lookup coverage, which is incomplete — most resulting positions past the opening book have no ECO entry at all, and for those, two truly transposed games could still receive different treatment if position identity weren't keyed explicitly. This research doesn't change any FR — it changes the "why" documented in spec.md's User Story 2, which I'm correcting there for accuracy.

**Alternatives considered**: Leaving the `eco|name` key as-is and only adding a cosmetic Position column. Rejected — it wouldn't fix the verified over-merging (the "London System" case), and the spec's Key Entities section explicitly requires position-based identity.

## Decision: `position_key` = existing `_fen_to_key()` applied to the existing `opening_fen` field

**Rationale**: `tree_viz.py` already computes `_fen_to_key(fen)` (strips halfmove/fullmove counters → 4-field FEN) and uses it as the join key into `eco_lookup` inside `_annotate_game_opening()`. This is the exact "already-normalized position identity used elsewhere in this project" the spec's Assumptions section refers to (it's also what `tree_engine.py`'s `_position_key()` produces for the separate Opening Tree view's `tree.sqlite`, using the same 4-field convention). `load_pgns()` already has the full `opening_fen` in scope when building each game's record — it just isn't reduced to the 4-field key and stored. Adding one field (`position_key: _fen_to_key(opening_fen) if opening_fen else None`) is the minimal Python-side change.

**Alternatives considered**: Re-deriving position identity from `tree.sqlite`'s `positions`/`edges` tables (the same data `load_tree()` reads for the Opening Tree tab) and joining games to it. Rejected as unnecessary — `opening_fen` per game is already exactly the FEN of the node in question; no join is needed, just normalization of a field already present.

## Decision: row's display Position (move-sequence) picks the most common sequence among contributing games — reusing existing precedent

**Rationale**: Games sharing a `position_key` can have different `opening_moves` (the literal transposition case — different orders, same result). `openOpModal()` already solves exactly this problem for the per-opening detail view: it counts move-sequence frequency among a group's games and picks the most common one to display/copy. Reusing that pattern for the aggregate row's Position column keeps one algorithm instead of two, and means FR-006 (no conflicting labels) is automatically satisfied — the row always shows one sequence, never a list.

**Alternatives considered**: Showing all distinct move orders for a merged row (e.g. "e3 e5 d4 / d4 e5 e3"). Rejected — spec's Edge Cases explicitly accepts that sort-by-Position won't perfectly cluster every transposed pair (since it sorts on the one displayed sequence), so showing multiple sequences per row would add complexity without changing that accepted limitation, and would clutter the table.

## Decision: `eco`/`name` for a row can be read directly from any one contributing game

**Rationale**: The data check above proved 0 position_keys map to more than one distinct `(eco, name)` — i.e., name is a pure function of position_key in this codebase, since both are ultimately derived from the same `eco_lookup[position_key]` dict lookup inside `_annotate_game_opening()`. There is no real risk of a merged row needing to reconcile conflicting opening names; FR-006 is satisfied by construction, not by picking a "winner" among competing labels.

## Decision: search-by-position (FR-007) matches against the row's displayed move-sequence text

**Rationale**: Simplest implementation consistent with the existing `nameFilter` substring-match behavior in `buildOpeningStats()` — extend the same `nameFilter` check to also test the row's move-sequence text (joined `opening_moves`), so one search box covers both without a second UI control, matching the "sort is enough" simplification already agreed for this feature.

**Alternatives considered**: A separate position-only search field. Rejected — spec's User Story 3 explicitly asks for the *existing* search box to also match position, not a new one.
