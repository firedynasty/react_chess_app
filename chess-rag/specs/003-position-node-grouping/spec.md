# Feature Specification: Position Column and Transposition Merging for Opening Stats

**Feature Branch**: `003-position-node-grouping`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "because I am filtering too by date see 9/05/2026 because I have a 1000 games loaded to now, winnows to 4 games I would like a groupby feature / filter on the table? and a new column for position so I can also sort by position ... Nodes in a move tree / opening tree — each move sequence is a node, and e3 e5 d4 is a child node of e3 e5 ... treat each one as keyed by move sequence — with the option to also key by resulting FEN so that transpositions (different move orders reaching the same position) collapse into the same node rather than being treated as separate stats buckets ... I can filter by node / position please" — refined in conversation: the user wants a familiar spreadsheet-style experience (click a column header to sort, e.g. sort by color then by position so related rows land next to each other) rather than an interactive click-to-drill or toggle-based rollup mechanism. A dedicated grouping/rollup control (collapsing many rows into fewer, broader ones) was explicitly descoped once sorting was confirmed sufficient for finding related rows.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See and sort by the position/node behind each row (Priority: P1)

While scanning the Openings Stats table, the user wants to see the actual move sequence (node/position) each row represents, not just the named opening, and wants to sort the table by that position — so rows that are structurally close in the opening tree (e.g. everything starting "e4 e5") land next to each other, the same way sorting any spreadsheet column clusters similar values.

**Why this priority**: This is the direct, concrete ask — a visible, sortable Position column — and is useful on its own, independent of the transposition-merge fix in User Story 2.

**Independent Test**: Open the Openings Stats tab, confirm every row shows its move sequence, and confirm clicking the Position column header sorts rows by that sequence (ascending/descending toggle like the existing sortable columns), with rows sharing a common opening sequence landing adjacent to each other.

**Acceptance Scenarios**:

1. **Given** the Openings Stats table is rendered, **When** the user looks at any row, **Then** the row displays the move sequence that reaches it (e.g. "b3 e5"), in addition to its existing ECO/opening name.
2. **Given** the Position column, **When** the user clicks its header, **Then** rows re-sort by move sequence, and clicking again reverses the sort order.
3. **Given** several rows whose move sequences share a common opening prefix (e.g. "e4 e5 Nf3" and "e4 e5 Bc4"), **When** the table is sorted by Position, **Then** those rows appear next to each other.

---

### User Story 2 - Key every row by its exact resulting position, not a coarser label (Priority: P1)

The user wants games that reach the same resulting board position by different move orders (e.g. "e3 e5 d4" vs "d4 e5 e3") to be counted together as one row's stats, not split across separate rows just because the moves were played in a different order — and, just as importantly, wants games that reach *different* resulting positions to never be silently lumped into one row just because they happen to share a coarse opening-name label.

**Why this priority**: This is the core correctness problem the user flagged. Verified against real data during planning: the table's current opening-name label is in some cases *coarser* than the actual position — e.g. one dataset had a single "Queen's Pawn: London" row silently combining 7 genuinely different resulting positions. Keying rows by exact position (rather than by name) fixes that over-merging directly, and as a side effect also guarantees true move-order transpositions are counted together, since both are really the same underlying fix: row identity = exact position, not a label that can be coarser (or, in principle, could diverge) from it. Unlike the descoped rollup (see Assumptions), this is a counting-correctness fix, not a navigation convenience, so it stays in scope regardless of how the user browses the table.

**Independent Test**: Load a data set with at least two games that reach the identical resulting position via different move orders. Confirm the Openings Stats table shows them as a single row with a combined game count and W/D/L, not two separate rows.

**Acceptance Scenarios**:

1. **Given** two games reaching the same resulting position via different move orders, **When** the Openings Stats table renders, **Then** both games are counted in the same row (same game count, combined W/D/L).
2. **Given** a merged row created from transposed games, **When** the user opens its detail view, **Then** all contributing games are listed together, regardless of which move order each one used to reach the position.

---

### User Story 3 - Find rows by typing a partial position (Priority: P2)

The user wants to type part of a move sequence into the existing search box and have it match rows by position as well as by opening name, so they can jump straight to "e4 e5" rows without scrolling through a sorted list.

**Why this priority**: A lighter-weight complement to sorting (User Story 1) for when the user already knows what position they're looking for; not required to fix the core fragmentation/visibility problem, so it can trail the first two stories.

**Independent Test**: Type a move-sequence fragment (e.g. "e4 e5") into the existing openings search box and confirm rows whose position contains that fragment are shown, alongside any rows already matched by opening name.

**Acceptance Scenarios**:

1. **Given** the existing openings search box, **When** the user types a move-sequence fragment, **Then** rows whose position matches that fragment remain visible, in addition to the existing name-matching behavior.
2. **Given** search text that matches neither a position nor an opening name, **When** the user searches, **Then** no rows are shown (consistent with today's no-match behavior).

---

### Edge Cases

- A row with only one contributing game must still display its position correctly (no broken display for singleton rows).
- Two named openings that are actually the same resulting position (per FEN) must merge under User Story 2 even though their opening names differ — the merged row must pick one consistent, sensible display name/position rather than showing conflicting labels.
- Sorting by Position uses plain move-sequence text, so positions that transpose into the same node but display a different representative move order will not necessarily sort adjacent to each other — this is an accepted limitation of text sort, not a merge failure (the merge in User Story 2 is about combined stats, not sort adjacency).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Openings Stats table MUST display, for every row, the move sequence (position/node) that produces it.
- **FR-002**: The Position column MUST be sortable, consistent with the table's existing sortable columns (ECO, Opening, Games, Win%).
- **FR-003**: Rows MUST be keyed by the resulting board position (already-normalized position identity used elsewhere in this project for the opening tree), not by the literal move-sequence text, so that games reaching the same position via different move orders are counted in the same row.
- **FR-004**: A row produced by merging transposed games MUST report a single combined game count and W/D/L reflecting all contributing games.
- **FR-005**: The per-row detail view MUST list every contributing game for a row, including ones that reached the row's position via a different move order than the row's displayed sequence.
- **FR-006**: When transposed games merge into one row, the row MUST show one clear, non-contradictory label rather than presenting multiple conflicting opening names as if the row were still separate entities.
- **FR-007**: The existing opening-name search box MUST also match against a row's position (move-sequence text), returning rows that match either the name or the position.

### Key Entities

- **Position Node**: A distinct resulting board position in the user's game history, identified by its normalized position identity (already used by this project's opening-tree engine) rather than by the literal move order that reached it. Carries an aggregated game count and W/D/L across every game that reached it, however it was reached.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every row corresponds to exactly one resulting position — no two rows ever represent the same exact position (the over-merging bug, e.g. one label spanning several distinct positions, is eliminated), and no single position's games are ever split across two or more rows just because they were reached via different move orders.
- **SC-002**: A user can locate all rows related to a given position (e.g. "all my e4 e5 games") in under 10 seconds using either sorting by Position or searching, without needing to open each row individually.

## Assumptions

- The resulting-position identity already computed by this project's opening-tree engine (used to detect shared positions for win/loss stats elsewhere in the tool) is authoritative for "same node" purposes; this feature does not introduce a new definition of position equality.
- This feature builds on Feature 002 (color breakdown) in the sense that both modify the same Openings Stats table, but is otherwise independent — it does not require 002 to be implemented first.
- Opponent-strength adjustment and rating-trend-over-time remain out of scope, as established in Feature 002.
- Existing per-row detail views (board, move list, game list, pinning) continue to work against whatever set of games a row currently represents, merged or not.
- **Descoped**: a dedicated group-by/rollup control that collapses many specific-position rows into fewer, broader ancestor rows was part of the original ask (motivated by a date filter narrowing 1000 games down to 4, fragmenting the table) but was explicitly dropped in favor of sorting once confirmed sufficient — sorting by Position clusters related rows visually without reducing the row count or combining their stats. If sorting alone later proves insufficient for very sparse filtered views, rollup can be specified as its own follow-up feature.
