# Implementation Plan: Batch Game ID Copy for Report Comparisons

**Branch**: `001-batch-report-ids` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-batch-report-ids/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Add two client-side copy actions to `data/tttstanley/tree_viewer.html`'s game-list toolbar — "Copy all ID(s)" and "Copy selected ID(s)" — that place a deduplicated, space-separated list of game IDs on the clipboard, scoped identically to the existing "Copy all PGN(s)" / "Copy selected PGN(s)" actions. This closes the gap between browsing games in the tree viewer and running the existing `report.py`, which already accepts 2+ game IDs on its command line and already generates both per-game reports and a combined wins-vs-losses comparison report — no change to `report.py` is required.

## Technical Context

**Language/Version**: Vanilla JavaScript (ES2017+, `async`/`await`, Clipboard API) embedded directly in `tree_viewer.html`; no build step or bundler. Python 3 for `report.py` (pre-existing, unchanged by this feature).

**Primary Dependencies**: None new. Browser `navigator.clipboard` API (already used by the existing `copyId`/`copyOne`/`copySelected`/`copyAll` functions). `report.py`'s existing dependencies (`openai`, `python-chess`) are untouched.

**Storage**: N/A. Reads from the in-memory `PGNS` object and `.game-chk` checkbox DOM state already present in `tree_viewer.html`. `report.py` continues to read `data/raw/chesscom/` and `tree.sqlite` in the bucket folder, unchanged.

**Testing**: No existing automated test harness for this static-HTML/Python-script project. Verification is manual: open `tree_viewer.html` in a browser, exercise the new buttons, inspect clipboard contents, and confirm a pasted ID list runs successfully through `report.py`.

**Target Platform**: Desktop browser, opened as a local static file (or via a simple static server) — single-user local tool, matching the file's current deployment.

**Project Type**: Single static web page (client-side only), paired with an existing, unmodified Python CLI script.

**Performance Goals**: Copy actions complete instantly (<100ms) for game lists up to roughly 50 games — well within what a synchronous DOM query + clipboard write already handles today for PGN copying.

**Constraints**: No backend/server introduced. Must not modify `report.py` or its CLI contract. Must not change the behavior of the existing `copyId`, `copyOne`, `copySelected`, or `copyAll` functions/buttons. Scoped only to `data/tttstanley/tree_viewer.html` — the sibling copies at `data/jyan_500/tree_viewer.html` and `against_computer/tree_viewer.html` have already diverged (different features per bucket) and are explicitly out of scope for this feature.

**Scale/Scope**: Single user (the repo owner), per-position game lists realistically in the 1–50 game range.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template (all principle sections contain placeholder text, no version/ratification date) — no ratified principles exist for this project yet. There is nothing to gate against, so this check passes vacuously. No complexity or violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/001-batch-report-ids/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

This is not a scaffolded src/tests project — it's a flat repo of static HTML galleries and small Python scripts per `CLAUDE.md`. The feature touches exactly one existing file:

```text
data/tttstanley/
├── tree_viewer.html   # MODIFIED: add "Copy all ID(s)" / "Copy selected ID(s)"
│                       #   buttons + copyAllIds()/copySelectedIds() JS functions,
│                       #   placed beside the existing copyAll()/copySelected()/
│                       #   copyId() functions and #games-toolbar buttons (~line 391-777)
├── report.py           # UNCHANGED: already accepts 2+ game_ids and already
│                       #   writes <id>.md per game + comparison.md (wins vs losses)
├── tree.sqlite          # UNCHANGED
└── reports/              # UNCHANGED: output destination for report.py runs

# Explicitly out of scope (already-diverged sibling copies, not touched):
data/jyan_500/tree_viewer.html
against_computer/tree_viewer.html
```

**Structure Decision**: Single-file, additive change inside `data/tttstanley/tree_viewer.html`. No new files, no new directories, no changes to `report.py` or any other bucket's copy of the viewer.

## Complexity Tracking

*No constitution violations — this section is not applicable (see Constitution Check above).*
