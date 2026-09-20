# Feature Specification: ECO Opening Explorer

**Feature Branch**: `004-eco-opening-explorer`

**Created**: 2026-09-19

**Status**: Draft

**Input**: User description: "Build an ECO opening reference/explorer page (similar in style/navigation to chess-rag/against_computer/tree_viewer.html) that lets a user browse and study different lines from the ECO (Encyclopedia of Chess Openings) classification, independent of any specific played games. Unlike tree_viewer.html's tree (which only shows openings encountered in the user's own game history), this page should let the user explore ECO opening lines as a reference — by ECO volume (A-E), by ECO code, and by opening name/family — so it can later be used as a reference source (e.g. to compare against played games or tag positions) elsewhere in chess-rag."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse the reference by ECO volume and code (Priority: P1)

A user wants to study the opening classification independent of any game they've played. They open the reference page, pick a volume (A–E), then narrow down to a specific ECO code (e.g. "C20"), and see every named line the classification recognizes under that code.

**Why this priority**: This is the core "reference, not game history" behavior the feature exists for — without it the page is indistinguishable from the existing played-games tree.

**Independent Test**: Can be fully tested by opening the page, selecting volume "C", then code "C20", and confirming every King's Pawn Game variation (Beyer Gambit, King's Head Opening, Wayward Queen Attack, etc.) appears with its own move sequence — with no dependency on any recorded game data.

**Acceptance Scenarios**:

1. **Given** the reference page is open at its default (all-volumes) view, **When** the user selects volume "C", **Then** only ECO codes C00–C99 and their lines are shown.
2. **Given** volume "C" is selected, **When** the user selects code "C20", **Then** the user sees the full list of named lines classified under C20, each showing its own move sequence and final position.
3. **Given** an ECO code with a large number of named lines (some codes classify 200+), **When** the user opens that code, **Then** the lines are presented in a way that stays navigable (e.g. grouped, paginated, or scrollable) rather than as one unbroken list.
4. **Given** the user switches the list to sort by move sequence instead of by code or name, **When** they locate a line (e.g. Slav Defense, "d4 d5 c4 c6", code D10), **Then** lines whose moves extend it (e.g. a Queen's Gambit Declined or Semi-Slav line reached by playing further moves) appear in the rows immediately below it, even though they carry a different ECO code — a direct result of sorting by the move sequence itself, since a longer sequence sorts right after the shorter sequence it starts with.

---

### User Story 2 - Search by opening name or family (Priority: P2)

A user knows (or partly remembers) the name of an opening or opening family — e.g. "Caro-Kann" or "Sicilian" — but not its ECO code or volume. They want to find every reference line matching that name, regardless of which code or volume it falls under.

**Why this priority**: Most people think in opening names before ECO codes; without name search the reference is only useful to someone who already knows the classification.

**Independent Test**: Can be fully tested by typing a family name (e.g. "Caro-Kann") into the search and confirming all matching lines appear across their respective codes, without first navigating by volume.

**Acceptance Scenarios**:

1. **Given** the reference page is open, **When** the user types a partial opening name into the search box, **Then** matching lines from anywhere in the classification (any volume/code) are shown, updating as the user types.
2. **Given** a search with no matches, **When** the user finishes typing, **Then** the page clearly indicates no matching lines were found instead of showing a blank or stale list.

---

### User Story 3 - Inspect a single line move-by-move (Priority: P2)

Having found a line (via volume/code browsing or name search), the user wants to see it played out on a board, one move at a time.

**Why this priority**: Seeing the position step by step is what makes this a genuine diagram/reference rather than a static list of names.

**Independent Test**: Can be fully tested by selecting a single line and stepping through its moves on the board one at a time, independent of the browse/search entry point used to reach it.

**Acceptance Scenarios**:

1. **Given** a selected reference line, **When** the user steps forward/backward through its moves, **Then** the board updates to reflect the position after each move, matching the board style already used elsewhere in chess-rag.

---

### Edge Cases

- What happens when an ECO code has an extremely large number of named lines (some codes classify 200+ variations) — how does the user find a specific one without endless scrolling?
- What happens when a search term matches nothing (typo, or an opening name not present in the classification)?
- What happens when two lines transpose to very similar names or near-identical final positions but arrived via different move orders — are they shown as distinct lines?
- What happens when the underlying reference dataset is missing the move sequence for a given code/position (data gap) — does the line still appear, just without a playable sequence, or is it hidden?
- What happens when the user is offline / the reference dataset hasn't been prepared locally yet — does the page fail clearly rather than showing an empty page with no explanation?
- What happens when a line's moves are a continuation of another line that belongs to a different ECO code (e.g. a Slav Defense line whose moves continue into a Queen's Gambit Declined or Semi-Slav code) — does sorting by move sequence surface that relationship, or does strict per-code grouping hide it?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST let users browse the ECO reference classification grouped by volume (A, B, C, D, E), independent of any recorded/played game.
- **FR-002**: System MUST let users narrow browsing to a single ECO code (e.g. "C20") and see every named line the classification recognizes under that code.
- **FR-003**: System MUST let users search/filter reference lines by opening name or partial name, returning matches across all volumes and codes (not just the currently selected one).
- **FR-004**: For each reference line, system MUST display its ECO code, its full opening name (including variation/sub-variation label where present), and the sequence of moves leading to its final position.
- **FR-005**: System MUST open a selected line into a detail view showing a chess board at that line's final position, its full annotated move list (e.g. "1. d4 d5 2. c4 c6"), and let the user step through the moves one at a time (forward and backward) — matching the look of the existing per-opening detail view elsewhere in chess-rag (board + move list together), rather than introducing a visually distinct pattern.
- **FR-006**: System MUST visually and functionally distinguish this reference view from the existing played-games tree — the reference view always shows the full ECO classification, never limited to openings the user has actually played.
- **FR-007**: System MUST indicate, for any browsed code or search result, how many lines matched, so users can judge whether they're looking at a complete or a large/truncated set.
- **FR-008**: System MUST clearly communicate when a reference line's move sequence is unavailable (data gap) rather than silently omitting the line or showing an empty board.
- **FR-009**: System MUST present reference lines as a passive browsing tool only: users can view and step through a line, but the page MUST NOT include recall-testing/quiz scoring or attempt-history tracking — that kind of trainer functionality is explicitly out of scope for this feature.
- **FR-010**: System MUST let users sort/order reference lines by move sequence in addition to by code and by name — sorting on the move sequence itself naturally places a line's longer continuations (which may fall under a different ECO code) in the rows immediately following it, instead of scattering them by code or alphabetical name.

### Key Entities *(include if feature involves data)*

- **Opening Line**: A single named entry in the ECO classification — has an ECO code (e.g. "C20"), a volume (its code's first letter, A–E), a name (which may include a colon-separated variation/sub-variation), a final position, and the sequence of moves that reaches it.
- **ECO Code**: A three-character classification bucket (e.g. "B10") that groups one or more Opening Lines that share a common early move sequence; belongs to exactly one volume.
- **ECO Volume**: One of five top-level groupings (A–E) that partitions all ECO Codes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from opening the reference page to viewing a specific ECO code's full set of named lines in under 15 seconds.
- **SC-002**: A user can find a specific opening by name (without knowing its ECO code) via search in under 10 seconds.
- **SC-003**: 100% of reference lines that have a known move sequence display that full sequence and a matching final board position; any line without a known sequence is clearly marked as such rather than shown as if complete.
- **SC-004**: The reference view never shows fewer than the full ECO classification's set of lines for a given code/search — i.e. it is never accidentally filtered down to only the user's played games.
- **SC-005**: A user sorting the list by move sequence can see a line's longer continuations — including ones under a different ECO code — in the rows immediately adjacent to it, without manually re-searching by name.

## Assumptions

- This feature is a new, standalone page dedicated to reference browsing (mirroring `tree_viewer.html`'s visual style and board/step-through interaction), not a new mode bolted onto the existing played-games tree page.
- This is a standalone lookup/reference tool, independent of any played-game data — it is not intended to connect to, tag, or be reused by the played-games tree or any other chess-rag feature.
- The existing local reference cache (`eco_openings.json`) currently stores only each position's ECO code and name, not its move sequence; the same upstream classification source it was built from does provide move sequences per line, so it is assumed that preparing this feature includes extending/regenerating that cached reference data to retain move sequences (a data-preparation step, not a change in scope for this spec).
- The full classification (roughly 12,000 named lines across ~500 ECO codes as of the current cache) is small enough to browse/search entirely client-side without requiring server-side pagination as a hard functional requirement; codes with very large line counts (200+) need a navigable presentation (grouping/scroll/pagination) per Edge Cases, but no specific mechanism is mandated.
- "Opening name/family" search is satisfied by substring matching against each line's full name (which already includes family and variation, e.g. "Sicilian Defense: Najdorf Variation"); no separate family taxonomy beyond what the ECO classification's names already encode is assumed to be required.
- "Sort by move sequence" (FR-010) is a plain sort on each line's move list (e.g. treating `["d4","d5","c4","c6"]` as a sort key) — nothing more than that. Its adjacency effect is a direct, automatic consequence of that sort: a line (`x x x`) sorts immediately before any line extending it (`x x x d`), which sorts immediately before a further extension (`x x x d e`), regardless of ECO code. No separate continuation graph, relationship data, or cross-referencing logic is built — the sort key alone produces this ordering.
- This feature is a passive reference/browsing tool only (per FR-009): no quiz, recall-testing, or attempt-history tracking is in scope.
