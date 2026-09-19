# Implementation Plan: Download PGN Button

**Branch**: `002-download-pgn-button` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-download-pgn-button/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Add a "Download PGN" button next to the existing "Copy PGN" button (`index.html:1204`) in the root `index.html` chess app. On click, it derives the same PGN export text `copyPgnToClipboard()` already computes — live `window.moveTree` serialized via `moveTreeToPgn()` if present, else `window.currentLoadedPgn` or `window.annotatedPgnWithVariations` — and saves it as a timestamped `.pgn` file using the browser's `Blob` + `URL.createObjectURL` + anchor-`download` pattern this file already uses elsewhere (`index.html:8795-8814`, `index.html:13107-13111`). When the live move tree path is used, the download additionally embeds `[%eval ±x.xx]` PGN comments per move, sourced read-only from the app's existing `window.positionEvalMap` (populated by "Get Eval", `index.html:7198-7264`) via a new `moveTreeToPgnWithEvals()` variant — `moveTreeToPgn()` itself, and therefore "Copy PGN", stays untouched. No new PGN-generation logic beyond that variant, no backend call, no new dependency.

## Technical Context

**Language/Version**: Vanilla JavaScript (ES6+), inline within the existing single-file `index.html` (no transpilation/build step)

**Primary Dependencies**: None new. Reuses existing globals/functions: `window.moveTree`, `moveTreeToPgn()` (`index.html:3162`), `window.currentLoadedPgn`, `window.annotatedPgnWithVariations`, `window.positionEvalMap` (FEN → White-POV centipawns, or a `mate_score=10000`-style encoded mate score — same convention as `chess-rag/ingest.py`'s `_fmt_eval`/`evaluate()`, see `index.html:2341-2343`), and the browser's native `Blob`/`URL.createObjectURL` APIs (already used for other downloads in this file, e.g. `fenQueueDownload()` at `index.html:8795`)

**Storage**: N/A — no persistence beyond the one-shot file the browser saves to the user's Downloads location; no change to in-memory state

**Testing**: No automated test harness exists for `index.html` today (static file, no build step, no test script). Validated manually per `quickstart.md`

**Target Platform**: Desktop web browsers (any browser supporting `Blob`/`URL.createObjectURL` and the anchor `download` attribute, already relied on elsewhere in this file); Vercel-hosted static page (`vercel.json` serves `index.html` directly, no build)

**Project Type**: Single-file static web app (existing architecture) — not a multi-package/web+backend split

**Performance Goals**: Download triggers with no perceptible delay (<100ms) after click; negligible for typical PGN sizes (a few KB of text)

**Constraints**: No new build tooling, bundler, or framework; must not alter or regress the existing "Copy PGN" clipboard behavior; must not introduce a second, divergent way of deriving base PGN text (moves/variations/user comments) from the one `copyPgnToClipboard()`/`moveTreeToPgn()` already use — eval tags are a strict *addition* layered on top for the download path only; must not trigger new engine analysis (evals are read-only from `window.positionEvalMap`, never computed on click)

**Scale/Scope**: One button + two functions (~40-60 lines total: `downloadPgn()` plus a `moveTreeToPgnWithEvals()` variant of `moveTreeToPgn()`), colocated with `copyPgnToClipboard()`/`moveTreeToPgn()` around `index.html:3214`, plus one button element next to `#copyPgnBtn` around `index.html:1204`; no new files or directories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled placeholder template (no principles have been ratified for this project). No gates are defined, so none apply here — nothing to check against, and nothing to justify in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-download-pgn-button/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
index.html                 # Existing single-file app (~13,000 lines). ALL changes for this
                            # feature land inside this file, inline with existing code:
                            #
                            #   <script> section, next to moveTreeToPgn()/copyPgnToClipboard()
                            #     (~line 3162-3241) — add:
                            #     - moveTreeToPgnWithEvals(rootNode): same traversal as
                            #       moveTreeToPgn(), but appends a [%eval ±x.xx]/#N tag
                            #       (formatted via a small helper mirroring ingest.py's
                            #       _fmt_eval) to each node's comment when
                            #       window.positionEvalMap[node.fen] is defined
                            #     - downloadPgn(): resolve PGN text — moveTreeToPgnWithEvals(
                            #       window.moveTree) when a live tree exists, else the same
                            #       fallback text copyPgnToClipboard() uses (no eval tags
                            #       possible in that path) — build a Blob, create a timestamped
                            #       filename, and trigger the download via a throwaway
                            #       <a download> element (same pattern as fenQueueDownload(),
                            #       line 8795)
                            #
                            #   Toolbar markup next to #copyPgnBtn (~line 1204) — add a
                            #     "Download PGN" <button onclick="downloadPgn()">
                            #
                            # No other files change. moveTreeToPgn() and copyPgnToClipboard()
                            # are reused unmodified, so "Copy PGN" output is unaffected.
```

**Structure Decision**: Single-file static web app (the project's existing and only architecture for this app — see `vercel.json`, which serves `index.html` directly with no build step). This feature adds one inline function and one button to `index.html` only; it does not introduce `src/`, `backend/`, `frontend/`, or any new project/package.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — Constitution Check found no ratified gates to satisfy, and this feature introduces no new project, dependency, or architectural pattern beyond what `index.html` already uses.
