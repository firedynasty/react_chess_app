# Mistake hop ( , and . )

**Verdict: KEEP**

Jump between the game's mistakes for one side with the comma and period keys.

**Entry point.** `⚠ White (0)` / `, ◀ ⚠` / `⚠ ▶ .` in the mini bar (index.html:1495-1497).

**Footprint.** 3 buttons · 36 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1494 | `mstSideBtn` | ⚠ White (0) | `mstToggleSide` |
| 1495 | `mstPrevBtn` | , ◀ ⚠ | `mstStep` |
| 1496 | `mstNextBtn` | ⚠ ▶ . | `mstStep` |

## Notes

- Three buttons, two keybindings, no backend. Cheapest feature in the app per unit of use. Keep.
