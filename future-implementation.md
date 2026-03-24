# Future Implementation Ideas

Prioritized improvements for the Stockfish.js analysis pipeline, based on lessons from the current implementation.

---

## 1. Upgrade the Stockfish.js Build (High Impact)

The current engine is Stockfish 11-12 era with **no NNUE** (neural network evaluation). It uses classical hand-crafted heuristics, which are significantly weaker on tactical positions — sacrifices, king walks, and forced lines often evaluate as 0.00 when modern Stockfish would see ±5 pawns.

**What to do:** Replace `stockfish.js` with a newer WASM build that includes NNUE. The official Stockfish repo and community forks publish `stockfish-nnue.wasm` builds. This single change would eliminate the majority of false blunders without any code changes.

**Watch out for:** NNUE builds are larger (~40MB for the net file). May need to lazy-load or cache the neural network file. Also verify the WASM build still exposes the same Web Worker `postMessage` interface.

---

## 2. Multi-PV for Better Variation Suggestions (Medium Impact)

Currently the analysis runs twice per mistake — once to detect the blunder, then `analyzePositionForVariation` runs again to get the principal variation (PV) line for the alternative move.

**What to do:** Use `setoption name MultiPV value 2` to get the top 2 lines in a single analysis pass. The first PV is the engine's best move; the second is the alternative. This halves analysis time for variation insertion.

**How it works:**
```
setoption name MultiPV value 2
position fen <fen>
go depth 15
```

Stockfish will output two sets of `info` lines per depth, each tagged with `multipv 1` or `multipv 2`. Parse both to get the best move and the runner-up in one pass.

---

## 3. Phase-Aware Thresholds (Medium Impact)

The current thresholds are static:
- BLUNDER: ≥ 200 centipawns
- MISTAKE: ≥ 100 centipawns

But eval swings mean different things in different phases:
- **Opening (moves 1-8):** A 150cp swing is common and often just a transposition preference. Currently handled by the opening skip filter.
- **Middlegame (moves 9-30):** 200cp is a reasonable blunder threshold.
- **Endgame (moves 30+):** Even 50cp can be the difference between winning and drawing. A pawn-up endgame that becomes equal is a real blunder that current thresholds might miss.

**What to do:** Scale thresholds by phase:
```javascript
function getThresholds(moveNumber) {
  if (moveNumber <= 8)  return { blunder: 300, mistake: 200 }; // opening: lenient
  if (moveNumber <= 30) return { blunder: 200, mistake: 100 }; // middlegame: standard
  return { blunder: 150, mistake: 75 };                         // endgame: strict
}
```

---

## 4. Regression Testing Against Chessis (Process)

Chessis uses Stockfish 18 at 1.2s/move — treat its annotations as ground truth. Keep a few annotated games from Chessis as regression tests.

**What to do:**
- Save 3-5 Chessis-annotated PGNs in a `test-games/` folder
- After any change to the analysis loop, run those games through the analyzer
- Compare: did blunder count go up or down? Did known blunders get detected? Did false positives appear?
- The depth 15 vs 18 comparison done manually in the original session could be scripted

**Key metric:** Match rate against Chessis annotations. Current baseline at depth 15: ~5/8 blunders matched.

---

## 5. Approach for Code Changes (Process)

Since the analysis pipeline lives in one large `index.html`, follow these guidelines when making changes:

1. **Use the EVAL DEBUG LOG** — paste it into chat to see exactly which move has wrong evals. The log shows `evalBefore → evalAfter swing [status]` for every move.

2. **Change one thing at a time** — depth OR thresholds OR engine behavior, never all at once. The interaction effects are hard to debug when multiple things change.

3. **Check the docs first:**
   - `stockfish-implementation.md` — explains the "why" behind current code decisions (single-pass eval, addEventListener, won-position filter, depth 15)
   - `research-stockfish.md` — the GitHub repo patterns and community practices that informed the implementation
   - This file — what's planned and why

4. **Don't re-introduce known bugs:**
   - Don't use `ucinewgame` per position (causes premature `bestmove`)
   - Don't replace `onmessage` per analysis call (causes race conditions) — use `addEventListener`/`removeEventListener`
   - Don't use a two-pass eval approach (causes `evalBefore = 0.00` on check/forced positions)

---

## 6. Won-Position Filter Refinement (Low Impact)

Current filter: skip blunder detection when `|prevEval| >= 600cp` (±6 pawns).

This is aggressive — a 6-pawn advantage can still be thrown away with a single bad move. Consider:
- Raising the threshold to ±10 pawns (1000cp) — only truly decided positions
- Or using a sliding scale: flag blunders in won positions only if the swing is enormous (e.g., from +8 to +1)

Low priority because won-position false blunders are cosmetic — they don't affect the useful annotations in competitive positions.
