# Feature Specification: Batch Game ID Copy for Report Comparisons

**Feature Branch**: `001-batch-report-ids`

**Created**: 2026-09-14

**Status**: Draft

**Input**: User description: "Extend the tree_viewer.html workflow so the user can select multiple games (via their existing 'Copy ID' per-row buttons and 'Copy all PGN(s)' button), collect the selected game IDs, and feed them into report.py to generate a per-game report (opening analysis, deviations, result) AND a combined comparison summary across all selected games — highlighting differences and similarities between games that were won vs. lost, so the user can see patterns in what led to wins vs. losses."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Copy all IDs for the current game list in one action (Priority: P1)

While browsing the games that reached a given opening/tree position, the user wants a single action that copies every listed game's ID into one paste-ready list, instead of clicking a per-game "Copy ID" button once for each game.

**Why this priority**: This is the core friction point today — building a multi-game comparison requires N separate single-ID copy actions. Removing that is the highest-value, smallest change.

**Independent Test**: Can be fully tested by opening a position with 3+ games listed, triggering the new "copy all IDs" action, and pasting the clipboard contents — delivers a space-separated list of all listed game IDs with no other click needed.

**Acceptance Scenarios**:

1. **Given** a game list showing 4 games at the active position, **When** the user triggers "copy all IDs", **Then** the clipboard contains all 4 game IDs, separated by single spaces, in the order shown.
2. **Given** a game list showing exactly 1 game, **When** the user triggers "copy all IDs", **Then** the clipboard contains that single ID (no separator artifacts).

---

### User Story 2 - Copy IDs of only the checked/selected games (Priority: P2)

The user wants to check specific games (e.g., a few losses and a few wins) and copy just those IDs, so they can build a targeted comparison group instead of always using the full list.

**Why this priority**: Builds directly on User Story 1's mechanism but narrows scope to a deliberate subset — valuable once the "copy all" flow exists, but a full list copy already unblocks the core comparison workflow.

**Independent Test**: Can be fully tested by checking 2 of 5 listed games and triggering "copy selected IDs" — delivers exactly the 2 checked IDs on the clipboard, independent of the other 3.

**Acceptance Scenarios**:

1. **Given** 5 games listed with 2 checked, **When** the user triggers "copy selected IDs", **Then** the clipboard contains exactly those 2 IDs, space-separated.
2. **Given** 0 games checked, **When** the user triggers "copy selected IDs", **Then** the system informs the user no games are selected and the clipboard is left unchanged.

---

### User Story 3 - Paste copied IDs straight into report generation (Priority: P3)

The user takes the copied ID list and runs it against the existing report-generation step, which already produces one report per game plus a combined summary that calls out differences and similarities between games that were won versus lost.

**Why this priority**: Confirms the end-to-end payoff of Stories 1 and 2, but depends on nothing new — it validates that the copied format is directly usable, not additional UI work.

**Independent Test**: Can be fully tested by copying IDs via either new action, pasting them as arguments to the existing report-generation step, and confirming it runs without needing any manual editing of the pasted text.

**Acceptance Scenarios**:

1. **Given** a clipboard holding 3 copied game IDs, **When** the user pastes them as arguments to the report-generation step, **Then** it accepts them unmodified and produces a per-game report for each plus one combined comparison summary.
2. **Given** the 3 games include both wins and losses, **When** the combined comparison summary is generated, **Then** it explicitly calls out patterns/differences observed between the winning game(s) and the losing game(s).

---

### Edge Cases

- What happens when "copy all IDs" is triggered on a position with zero games? The action should be unavailable or a no-op with a clear message, matching how the existing "Copy all PGN(s)" toolbar already hides itself when there are no games.
- What happens when the same underlying game appears twice in the current list (e.g., duplicate entries across a merged view)? The copied ID list must not contain duplicate IDs.
- How does the system handle a browser that denies clipboard write access? The action should fail visibly (not silently) and match the fallback behavior already used by the existing per-row "Copy ID" button.
- What happens when only 1 game's ID is copied and pasted into report generation? A per-game report is produced; no combined comparison is produced (this is existing, unchanged behavior since comparison requires 2+ games) — the UI should not imply a comparison will appear for a single ID.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The game list view MUST provide an action to copy the IDs of every game currently listed (i.e., matching the scope of the existing "Copy all PGN(s)" action) as a single list on the clipboard.
- **FR-002**: The game list view MUST provide an action to copy the IDs of only the checked/selected games (i.e., matching the scope of the existing "Copy selected PGN(s)" action) as a single list on the clipboard.
- **FR-003**: Copied ID output MUST contain only game IDs separated by single spaces — no PGN text, headers, or other formatting — so it can be pasted directly as command-line arguments to the existing report-generation step.
- **FR-004**: The copied ID list MUST NOT contain duplicate IDs, even if the same game appears more than once in the current view.
- **FR-005**: When "copy selected IDs" is triggered with zero games checked, the system MUST notify the user that nothing is selected and MUST leave the clipboard unchanged.
- **FR-006**: Both new copy actions MUST give the user visible confirmation of success (and how many IDs were copied), consistent with the confirmation style already used by the existing copy buttons.
- **FR-007**: The existing report-generation step MUST continue, unchanged, to accept 2 or more game IDs and produce both an individual report per game and one combined comparison report that highlights differences and similarities between games won and games lost.

### Key Entities

- **Game**: A single played game shown in the list — has an ID, players, result (win/loss/as which color), date, and a source link; already exists in the current view.
- **Selection**: The set of games the user has checked in the current view, used to scope the "copy selected IDs" action.
- **Comparison Report**: The combined output (already produced by the existing report-generation step whenever 2+ game IDs are supplied) summarizing per-game findings plus a cross-game section on what differed or matched between wins and losses.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Building a paste-ready ID list for a multi-game comparison takes 1 click, regardless of how many games are in the list — down from 1 click per game today.
- **SC-002**: 100% of copied ID lists, when pasted as arguments into the existing report-generation step, are accepted without any manual edits (no stray characters, no PGN content).
- **SC-003**: For any run covering 2+ games with a mix of wins and losses, the resulting combined report includes an explicit summary of differences/similarities observed between the winning and losing games.
- **SC-004**: Across group sizes from 1 to 20 games, "copy selected IDs" returns exactly the checked games' IDs with zero unintended extras or omissions, every time.

## Assumptions

- The existing report-generation step already produces a combined comparison report (with a wins-vs-losses summary) whenever it is given 2 or more game IDs; this feature is scoped to making it faster and less error-prone to get those IDs out of the game list view, not to changing what the report contains.
- Copied ID output is a bare, space-separated list of IDs — matching what the report-generation step already accepts as its game-ID arguments — not a full ready-to-run command line; the user still invokes report generation themselves afterward.
- "All games" scope for the new copy-all-IDs action matches whatever the existing "Copy all PGN(s)" action currently copies (the games at the active opening/tree position), not every game in the entire dataset.
- This is a single-user local tool with no authentication or multi-user permission concerns; clipboard access is assumed available in the same way the existing copy buttons already assume it.
- No change to report.py itself is required for this feature; it already supports multi-ID comparison runs.
