# Phase 1 Data Model: Download PGN Button

This feature introduces no new persisted entities and no new in-memory data structure. It reads the same PGN Export Text value already defined and computed by `copyPgnToClipboard()`/`moveTreeToPgn()` (see `001-move-tree-context-menu/data-model.md` for the full Move Node shape those functions traverse). This document covers only what's new: the resolution/output flow for a download.

## Value: PGN Export Text

- **Source (in priority order)**, identical to `copyPgnToClipboard()` (`index.html:3214-3221`):
  1. `moveTreeToPgn(window.moveTree)` — if `window.moveTree` is truthy, serialize the live tree (reflects any in-session edits/annotations).
  2. `window.currentLoadedPgn` — the most recently loaded PGN text, if no live tree exists.
  3. `window.annotatedPgnWithVariations` — final fallback.
- **Absence**: If none of the above yield a non-empty string, there is no PGN Export Text available (spec FR-005 / Edge Case).

## Value: Eval Tag (download-only)

Attached only when serializing via `moveTreeToPgnWithEvals()`, and only per move where data exists.

| Field | Source | Format |
|---|---|---|
| Lookup key | `node.fen` (each Move Node already carries this — see `001-move-tree-context-menu/data-model.md`) | — |
| Raw value | `window.positionEvalMap[node.fen]` — White-POV centipawns, or a mate score encoded as `scoreValue > 0 ? 10000 - scoreValue : -10000 - scoreValue` (same convention as `chess-rag/ingest.py`'s `evaluate()`) | integer, `undefined` if not yet computed |
| Formatted tag | `undefined` → omit entirely. Otherwise: `abs(value) >= 9900` → `` `#${value > 0 ? '' : '-'}${10000 - abs(value)}` ``; else → `` `[%eval ${(value / 100).toFixed(2)}]` `` (mirrors `ingest.py`'s `_fmt_eval`) | PGN comment text |
| Placement | Appended to the node's existing comment (space-separated) if one exists; otherwise becomes the node's whole `{...}` comment for serialization purposes only — the in-memory `node.comment` itself is never mutated (see State transitions below) | — |

**Absence is not an error**: a node with no entry in `positionEvalMap` simply serializes with whatever comment it already had (or none), per spec FR-008.

## Value: Download Filename

| Component | Value |
|---|---|
| Prefix | `game_` (mirrors the `puzzles_` prefix convention used by `fenQueueDownload()`, `index.html:8811`) |
| Timestamp | Current local time formatted so it contains no characters invalid in filenames (no `:`); e.g. derived from `new Date().toISOString()` with `:`/`T` replaced |
| Extension | `.pgn` |

**Uniqueness rule** (FR-004, SC-002): Because the timestamp component has second-level granularity, two downloads triggered by the same user more than one second apart always get distinct filenames. Two downloads within the same second are the only theoretical collision case — acceptable per spec Assumptions (same-session, same-machine uniqueness only; not a hard concurrency guarantee).

## State transitions

None. This feature is a pure read of existing state (PGN Export Text, Position Evaluation Data) followed by a one-shot browser file save. It does not mutate `window.moveTree` (including any node's `comment`/`annotation` field), `window.currentLoadedPgn`, `window.annotatedPgnWithVariations`, `window.positionEvalMap`, or any other existing global — eval-tag text is composed only in the serialized output string, never written back onto the node.

## Relationship to existing "Copy PGN" data flow

```text
                 ┌─────────────────────────────┐
                 │   PGN Export Text resolver   │
                 │ (moveTree → currentLoadedPgn │
                 │   → annotatedPgnWithVariations)│
                 └───────────────┬─────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
        copyPgnToClipboard()            downloadPgn()  (new)
        → moveTreeToPgn(tree)           → if moveTree: moveTreeToPgnWithEvals(tree)
          (or fallback text)              (reads positionEvalMap per node, read-only)
        → navigator.clipboard             else: same fallback text as Copy PGN
                                         → Blob → object URL → <a download> click
```

Both consumers share the same base resolver logic (moves/variations/user comments); `downloadPgn()` layers eval tags on top only when a live tree is available, and never mutates `positionEvalMap` or the tree — so "Copy PGN" and the non-eval parts of a download can never disagree (spec SC-003), while the download alone additionally reflects available eval data (spec SC-005).
