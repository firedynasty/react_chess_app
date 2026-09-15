# Feature Specification: Opening Color Column

**Feature Branch**: `002-opening-color-breakdown`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "In tree_viewer.html's Openings Stats table (rendered by renderOpenings() in tree_viz.py), the user can't tell which color (White or Black) they played for each opening row — the table only shows ECO, Opening name, Games, W/D/L, Win%, and a bar. Since the same opening name can be reached as either color (or the row could mix games from both colors), the user needs a way to see the color split. Add a per-row color indicator/breakdown to the Openings Stats table so the user can immediately tell whether their W/D/L record for a given opening came from playing White, Black, or a mix of both — this is the first of several planned stat enhancements to this table (opponent-strength adjustment and rating trend are later, separate bullets, out of scope for this feature)." — refined in conversation: rather than a toggle that splits or hides colors, every row should simply always be scoped to one color, with a sortable Color column — the same familiar spreadsheet sort-by-column experience as the table's other columns, no on/off mode to manage.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See which color each row's stats belong to (Priority: P1)

While scanning the Openings Stats table, the user wants to know, at a glance, whether the win/draw/loss record shown for a row happened while they played White or Black, without opening the row's detail view to find out.

**Why this priority**: This is the exact gap the user hit — the table currently gives no color signal at all, so a strong or weak win rate can't be interpreted (e.g. "0% with the Nimzo-Larsen" is a different finding if it's one Black loss vs. one White loss). Without this, every other stat in the table is ambiguous. This alone delivers the requested value.

**Independent Test**: Open the Openings Stats tab with a data set containing an opening played only as White, one played only as Black, and one played as both. Confirm every row visibly and unambiguously shows one color, with no additional click needed.

**Acceptance Scenarios**:

1. **Given** an opening the user has only ever played as White, **When** the Openings Stats tab is rendered, **Then** that opening appears as one row with a clear White indicator.
2. **Given** an opening the user has only ever played as Black, **When** the Openings Stats tab is rendered, **Then** that opening appears as one row with a clear Black indicator.
3. **Given** an opening the user has reached as both White and Black, **When** the Openings Stats tab is rendered, **Then** it appears as two separate rows — one scoped to the White games, one scoped to the Black games — each with its own game count and W/D/L, never combined into a single ambiguous row.

---

### User Story 2 - Sort by color to review one side of the repertoire together (Priority: P2)

The user wants to click the Color column header, the same way they already sort by ECO, Opening, Games, or Win%, and have all the Black rows sort together (and likewise for White), so they can review one side of their repertoire as a contiguous block.

**Why this priority**: Once color is a visible, per-row attribute (User Story 1), sorting by it is a small, natural extension using the table's existing sort mechanism — valuable but not required to fix the immediate "I can't tell" problem.

**Independent Test**: With the Color column from User Story 1 in place, click its header and confirm all White rows group together and all Black rows group together (sorted, not filtered — both colors remain visible); click again to reverse the order.

**Acceptance Scenarios**:

1. **Given** the Openings Stats table with both White and Black rows, **When** the user clicks the Color column header, **Then** rows re-sort so all rows of one color appear together, followed by all rows of the other color.
2. **Given** the table sorted by color, **When** the user clicks the Color header again, **Then** the sort order reverses.
3. **Given** the table sorted by color, **When** the user clicks a different column's header (e.g. Win%), **Then** the table re-sorts by that column instead, same as it does today for the existing columns.

---

### Edge Cases

- An opening played as only one color must never produce an empty or zero-game row for the other color.
- Two rows for the same opening (one White, one Black) must be independently sortable, filterable, and pinnable — sorting or filtering must never accidentally reunite or separate them beyond what the user's action implies.
- The per-opening detail view (opened by clicking a row) must only list the games matching that row's specific color, not the opening's games from both colors.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Openings Stats table MUST always scope each row to a single color (White or Black); an opening played as both colors MUST appear as two separate rows.
- **FR-002**: Every row MUST show a clear, unambiguous color indicator.
- **FR-003**: The color indicator MUST be visible directly in the table row, requiring no additional click or navigation to see it.
- **FR-004**: The Color column MUST be sortable, consistent with the table's existing sortable columns (ECO, Opening, Games, Win%).
- **FR-005**: The per-opening detail view (opened by clicking a row) MUST list only the games matching that row's color.
- **FR-006**: Splitting rows by color MUST work together with the table's existing filters (time control, date range, opening-name search) rather than replacing them — filters apply to each color's row independently.

### Key Entities

- **Opening Stats Row**: An aggregated record for one opening (identified by ECO code + opening name) *and* one color, within the current filters. Each (opening, color) combination that has at least one game produces its own row.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user looking at any row in the Openings Stats table can state which color it represents within 2 seconds, without clicking into the row.
- **SC-002**: 100% of openings played as both colors appear as two distinct rows, each with correct, non-overlapping game counts that sum to the opening's total games.
- **SC-003**: Clicking the Color column header groups all same-color rows together, using the same familiar interaction as the table's other sortable columns.

## Assumptions

- Color is determined from each game's existing recorded `my_color` value (White/Black); no new data collection or re-classification of historical games is required.
- Splitting rows by color is always-on (no toggle to manage); this replaces the originally proposed "group by color" toggle once confirmed that a plain, always-split, sortable Color column is simpler and sufficient.
- There is no longer a combined "both colors" row for an opening played as both; a user wanting the opening's total across colors would read both rows. If a combined total view turns out to be wanted later, it can be specified as a follow-up.
- Opponent-strength adjustment and rating-trend-over-time enhancements to this table are explicitly out of scope for this feature and will be specified separately.
