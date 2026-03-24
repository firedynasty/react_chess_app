# Stockfish.js Implementation Notes

Lessons learned from building and debugging browser-side chess analysis in this project.

---

## What Version Is Running

**Current:** Stockfish 17.1 with NNUE (lite-single build), loaded from `src/stockfish-17.1-lite-single-03e3232.js` + `.wasm` (~7MB total). This is the nmrugg/stockfish.js build used by Chess.com.

**Previous (replaced):** The old `stockfish.js` in root was a multi-variant Stockfish compiled to JavaScript (not WASM), based on the Daniel Dugovic fork (~Stockfish 11-12 era, no NNUE). That version evaluated positions using classical hand-crafted heuristics, which caused many false blunders on tactical positions.

The NNUE upgrade dramatically improves evaluation accuracy:
- Neural network evaluation trained on millions of positions (~3400+ ELO vs ~3200 classical)
- Complex tactical positions (sacrifices, forced king walks, pawn promotions) are evaluated much more accurately
- Far fewer positions incorrectly evaluated as 0.00

Chessis uses Stockfish 18 at 1.2s per move. This repo now runs Stockfish 17.1 NNUE in the browser — the gap is much smaller than before. See `research-stockfish-nnue.md` for the full research notes on this upgrade.

---

## How Stockfish Communicates (UCI Protocol)

Stockfish runs as a Web Worker. All communication is message-passing:

```
You send:  "position fen <fen>"
You send:  "go depth 15"
Engine outputs: "info depth 1 score cp 32 ..."
               "info depth 2 score cp 45 ..."
               ...
               "info depth 15 score cp 120 pv e2e4 e7e5 ..."
               "bestmove e2e4 ponder e7e5"
```

The score in `info` lines is **always from the side-to-move's perspective** — positive means good for whoever is about to move.

---

## The evalBefore = 0.00 Problem

### What we saw
Early reports showed this pattern repeatedly:

```
6. exf7+:  0.00 → 0.00   swing  0.00  [skip(OPENING)]
6... Ke7:  0.00 → -19.55  swing -19.55  [BLUNDER]
7. Bg5+:  19.55 → 0.00   swing -19.55  [skip(WON-POS)]
```

The move `Ke7` (forced king move after check) was flagged as a 19-pawn blunder. Obviously wrong.

### Root cause
The old code used a **two-pass approach**:

**Pass 1** — evaluate every position and store raw scores in an array:
```js
evaluations[0] = starting position
evaluations[1] = after move 0
evaluations[2] = after move 1
...
```

**Pass 2** — loop through history, read `evaluations[i]` and `evaluations[i+1]`, convert perspectives, compute swing.

The problem: for positions after a check (only one legal response), Stockfish sometimes outputs `bestmove` almost immediately with very few or no `info depth` lines — leaving `finalEval` at its initial value of `0`. So `evaluations[11]` (after `exf7+`) would be `0` even though White is clearly winning.

Then in Pass 2:
- `evalBefore` for `Ke7` = 0 (wrong — should be ~+19)
- `evalAfter` for `Ke7` = 19.55 (correct)
- swing = 0 - 19.55 = -19.55 → false BLUNDER

### The fix: single-pass, carry prevEval forward

Inspired by the `chess-blunders` and React Stockfish examples on GitHub:

```js
let prevEval = 0;  // starting position ≈ equal

for (let i = 0; i < history.length; i++) {
    chess.move(move.san);
    const fenAfter = chess.fen();

    const sfResult = await analyzePosition(fenAfter, depth);

    // Convert to White's perspective using whose turn it is AFTER the move
    const currentEval = chess.turn() === 'w' ? sfResult.evaluation : -sfResult.evaluation;

    const swing = isWhite
        ? currentEval - prevEval      // White moved: positive = improvement
        : prevEval - currentEval;     // Black moved: negative = Black hurt themselves

    // ... classify swing as BLUNDER / MISTAKE / ok ...

    prevEval = currentEval;  // carry forward — never re-read a stored value
}
```

Key insight: `prevEval` is always the correctly-computed result from the previous iteration. We never go back and re-read a raw Stockfish score. So the `0.00` from a check position only affects that one move's own classification — not the next move's `evalBefore`.

---

## Perspective Conversion

Stockfish scores are from **side-to-move perspective**. We normalize everything to **White's perspective** for consistent swing calculation:

```js
// After each move, chess.turn() tells us whose turn is NEXT:
// - chess.turn() === 'b' → White just moved → score is from Black's POV → negate
// - chess.turn() === 'w' → Black just moved → score is from White's POV → keep

const currentEval = chess.turn() === 'w' ? rawEval : -rawEval;
```

Display values are then flipped back to the mover's perspective:
```js
evalBeforeForDisplay = isWhite ? prevEval    : -prevEval;
evalAfterForDisplay  = isWhite ? currentEval : -currentEval;
```

---

## Why Depth 15 Beats Depth 18

Counter-intuitively, **depth 15 gives more accurate blunder detection than depth 18** with this engine.

The timeout is set to 8 seconds per position. At depth 18, complex tactical positions (sacrifices, king hunts) can exceed this timeout. When timeout fires, `finalEval` is whatever partial depth was reached — sometimes only depth 3-5, sometimes 0 if no `info` lines arrived in time.

At depth 15, the search completes reliably within the time budget and returns a stable evaluation.

Depth comparison on the same game vs Chessis (Stockfish 18):

| Depth | Chessis matches | False blunders |
|-------|----------------|----------------|
| 18    | 2/8            | many           |
| 15    | 5/8            | few            |

**Default depth is set to 15.**

---

## False Blunders: The Won-Position Filter

Even with the single-pass fix, big eval swings appear in already-decided positions. Example:

```
18... Nxe5:  -31.46 → 0.00   swing +31.46  [skip(WON-POS)]
```

After White is up +31 pawns, every move by both sides creates huge swings because the engine's evaluation fluctuates in overwhelming positions. These are not real blunders.

**Fix:** skip blunder detection if the position was already decided before the move:

```js
const DECIDED = 600;  // ±6 pawns

const isWonPosition = Math.abs(prevEval) >= 600;
if (isWonPosition) {
    filterReason = 'WON-POS';
    // don't flag anything here
}
```

---

## The `analyzePosition` Function: addEventListener vs onmessage

Early implementation replaced `stockfish.onmessage` for each position:

```js
stockfish.onmessage = analysisHandler;   // set
// ... analysis runs ...
stockfish.onmessage = handleStockfishMessage;  // restore
```

Problem: if Stockfish produces output **after** the promise resolves (late-arriving `info` lines from a previous position), the new `analysisHandler` for the next position could receive them. This caused random `0.00` values that looked like the engine returned nothing.

**Fix:** use `addEventListener` / `removeEventListener` (the standard pattern from GitHub examples):

```js
const handler = (e) => {
    const line = e.data;
    if (line.startsWith('info') && line.includes('score')) {
        // update finalEval ...
    }
    if (line.startsWith('bestmove')) {
        stockfish.removeEventListener('message', handler);  // clean up
        resolve({ evaluation: finalEval, depth: currentDepth });
    }
};

stockfish.addEventListener('message', handler);
stockfish.postMessage('position fen ' + fen);
stockfish.postMessage('go depth ' + targetDepth);
```

Each analysis call has its own isolated handler that removes itself when done. No global state mutation.

---

## ucinewgame: Don't Use It Per-Position

We tried sending `ucinewgame` before each position to clear hash tables and prevent stale cache hits. This made things **worse** — it caused Stockfish to sometimes emit `bestmove` before completing even depth 1, leaving `finalEval = 0` for the whole position.

`ucinewgame` is meant to be sent once at the start of a new game, not between every position in a sequential analysis loop. Remove it from `analyzePosition`.

---

## The Eval Debug Log

To diagnose blunder detection issues, each report includes a full per-move debug section:

```
EVAL DEBUG LOG
----------------------------------------------------------------------
(positive eval = good for the side that just moved)
5... c5:   0.74 → 0.00   swing -0.74   [skip(OPENING)]
6. exf7+:  0.00 → 0.00   swing  0.00   [skip(OPENING)]
6... Ke7:  0.00 → 0.00   swing  0.00   [skip(OPENING)]
13. Bxd5+: 2.23 → 0.00   swing -2.23   [BLUNDER]
```

Columns: `notation move: evalBefore → evalAfter  swing  [status]`

Status values:
- `ok` — no issue, not flagged
- `BLUNDER` — swing ≤ -200cp (−2 pawns)
- `MISTAKE` — swing ≤ -100cp (−1 pawn)
- `skip(OPENING)` — moveNum ≤ 8, swing < BLUNDER threshold
- `skip(WON-POS)` — |prevEval| ≥ 600cp before move

Paste this section into chat to debug any incorrect annotations.

---

## Variation Insertion After Analysis

After blunders/mistakes are detected, Stockfish runs again for each one using `analyzePositionForVariation` which returns the full **principal variation (PV)** — the best continuation line. This is inserted as a branch in the move tree via `addVariationToPgn`, so the board shows the alternative line and draws arrows when you navigate to that position.

For Chessis-annotated PGN (with `{Best: move}` comments), the same pipeline runs using the Chessis best moves as starting points instead of detected mistakes.
