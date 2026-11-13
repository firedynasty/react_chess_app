# Type/Play panel + play vs Stockfish

**Verdict: KEEP**

Type moves instead of dragging, castle shortcuts, and play a full game against Stockfish from the start or from the current position.

**Entry point.** `Type/Play` (1616) → `#typedMovePanel`; `New Game` / `From Position` (1439-1440).

**Footprint.** 10 buttons · 57 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1410 | `—` | Apply | `applyTypedMove` |
| 1412 | `—` | Copy + Lichess Editor | `copyTypedStatusAndOpenEditor` |
| 1416 | `—` | 📋 Copy | `writeText, getElementById` |
| 1438 | `—` | New Game | `startStockfishGame` |
| 1439 | `—` | From Position | `startStockfishFromPosition` |
| 1446 | `—` | Lichess ↗ | `getTypedChess, fen, open, replace` |
| 1615 | `toggleTypedMoveBtn` | Type/Play | `getElementById, gradient, stopStockfishGame` |
| 1618 | `castleBtn` | Castle | `showCastleMenu` |
| 12576 | `—` | ' + icon + ' O-O (\u2192' + dir + ') | `applyCastle` |
| 12580 | `—` | ' + icon + ' O-O-O (\u2192' + dir + ') | `applyCastle` |

## Notes

- Self-contained (index.html:17925-18060 and 18060+ for play-vs-engine). Keep.
- Its `📋 Copy` (1417) and `Copy + Lichess Editor` (1413) are two more clipboard variants.
