# Stockfish NNUE Research Notes

Research on upgrading from classical Stockfish.js to NNUE-enabled builds for client-side chess analysis.

---

## Why NNUE Matters

**Classical Stockfish (pre-NNUE, what this project used before):**
- Rating: ~3200 ELO
- Evaluation: hand-crafted heuristics
- False blunders: many — weak on sacrifices, king walks, complex tactics
- Equivalent to Stockfish 11-12 era

**Stockfish 17.1+ with NNUE:**
- Rating: ~3600 ELO (~400 ELO stronger)
- Evaluation: neural network trained on millions of positions
- Understands complex positions that classical eval completely misses
- Fewer false positives in blunder detection

---

## Available Builds (nmrugg/stockfish.js)

Source: https://github.com/nmrugg/stockfish.js (powers Chess.com)

| Build | Size | Threads | NNUE | Notes |
|-------|------|---------|------|-------|
| `stockfish-17.1-single` | ~100MB (6 WASM parts) | Single | Full | Strongest, large download |
| `stockfish-17.1` | ~100MB (6 WASM parts) | Multi | Full | Requires SharedArrayBuffer + COOP/COEP headers |
| `stockfish-17.1-lite` | ~7MB WASM | Multi | Lite | Requires SharedArrayBuffer + COOP/COEP headers |
| `stockfish-17.1-lite-single` | ~7MB WASM | Single | Lite | **Best for this project** — no special headers needed |
| `stockfish-17.1-asm` | ~10MB JS | Single | No | ASM.js fallback for old browsers |

### Why lite-single is the right choice

- **Single-threaded**: no need for `SharedArrayBuffer`, `Cross-Origin-Embedder-Policy`, or `Cross-Origin-Opener-Policy` headers. Works on any hosting (Vercel, GitHub Pages, etc.)
- **Lite NNUE**: smaller network (~5MB embedded in WASM) but still ~3400+ ELO — dramatically better than classical eval
- **7MB total**: acceptable download for a chess analysis tool
- **Same UCI interface**: drop-in replacement, no code changes needed beyond the Worker path

### Multi-threaded builds require special headers

If upgrading to multi-threaded in the future, the server must send:
```
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Opener-Policy: same-origin
```
Without these, `SharedArrayBuffer` is unavailable and the engine will fail to initialize.

---

## Key GitHub Repos Studied

### 1. nmrugg/stockfish.js (Production-grade, Chess.com)

- Stockfish 17.1/18 with full NNUE support
- Multiple flavors via npm: `npm install stockfish`
- NNUE network is **embedded** in the WASM file — no separate `.nnue` file needed
- UCI option: `setoption name Use NNUE value true`

### 2. hi-ogawa/stockfish-nnue-wasm-demo (Learning resource)

- Complete React/TypeScript implementation
- Deployed on Vercel: https://stockfish-nnue-wasm.vercel.app/
- Shows NNUE integration, game analysis, blunder detection

### 3. lichess-org/stockfish-web (Official build scripts)

- Where Lichess builds their WASM versions
- Contains Stockfish 18 with NNUE
- Two network sizes: big (~100MB) and small (~5MB)

### 4. chess-blunders (Blunder detection library)

- `prevEval` carry-forward pattern (adopted in this project)
- Single-pass analysis loop
- `addEventListener`/`removeEventListener` per position

---

## UCI Options for NNUE

```
setoption name Use NNUE value true    // Enable neural network eval
setoption name Threads value 4        // Multi-core (multi-threaded builds only)
setoption name Hash value 128         // Transposition table size in MB
setoption name MultiPV value 2        // Top N lines (for variation suggestions)
```

For the lite-single build, only `Use NNUE` and `Hash` are relevant (single-threaded, no multi-core).

---

## Lichess Blunder Classification Thresholds

From studying the Lichess codebase (`ui/analyse/src/`):

```javascript
function classifyMove(prevScore, newScore) {
  const diff = newScore - prevScore;
  if (diff <= -300) return 'blunder';     // ??
  if (diff <= -150) return 'mistake';     // ?
  if (diff <= -50)  return 'inaccuracy';  // ?!
  if (diff >= 50)   return 'good';        // !
  if (diff >= 150)  return 'brilliant';   // !!
  return 'normal';
}
```

This project uses 200cp/100cp (blunder/mistake) — slightly more lenient, which was appropriate for the old classical engine. With NNUE, tightening to Lichess thresholds (300/150) may be worth testing.

---

## What Changed in This Project

**Before:** Root `stockfish.js` — old multi-variant Stockfish compiled to JS (no NNUE, ~Stockfish 11-12 era, 1.5MB)

**After:** `src/stockfish-17.1-lite-single-03e3232.js` + `.wasm` — Stockfish 17.1 with lite NNUE (~7MB total)

Changes made:
1. Worker path: `new Worker('stockfish.js')` → `new Worker('src/stockfish-17.1-lite-single-03e3232.js')`
2. Added `setoption name Use NNUE value true` after UCI init
3. Engine info display updated to "Stockfish 17.1 NNUE"

No other code changes needed — the UCI interface is identical. The `analyzePosition` function, single-pass eval loop, won-position filter, and variation insertion all work unchanged.

---

## Expected Improvements

With NNUE:
- Far fewer false blunders on tactical positions (sacrifices, king hunts)
- More accurate eval in quiet positional positions
- Better agreement with Chessis (Stockfish 18) annotations
- May be able to increase depth back to 18 since NNUE evaluations converge faster

Worth testing: run the same games that produced false blunders with the old engine and compare results.
