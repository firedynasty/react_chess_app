# View Text modal

**Verdict: MERGE into clipboard-sprawl**

Show the game as text and copy it formatted or as one line.

**Entry point.** `View Text` (index.html:1615) → `#textViewModal`.

**Footprint.** 3 buttons · 47 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**Other files.** `textReformatter.html` · `pgn_single_line.html`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1614 | `viewTextBtn` | View Text | `openTextViewModal` |
| 1901 | `—` | ✕ | `getElementById` |
| 1905 | `—` | Copy Formatted | `copyTextViewFormatted` |

## Notes

- Three buttons. `Copy One-Line` here duplicates `1-Line`'s `Copy single line` (1773), `lnCopyVarOneLine` (1545) and `practiceCopyOneLine` (1794). Four one-line copies.
