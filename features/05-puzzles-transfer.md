# Transfer to puzzles (paste rows → puzzles table)

**Verdict: KEEP**

Paste `Copy Move Info` rows into the ☰ pane, pick a category, Send — they go into the shared Supabase puzzles table, skipping FENs already in that category.

**Entry point.** `Hide ▴` / `📋 Copy all rows` / `⬆ Send to puzzles` in the ☰ pane (index.html:1095-1108).

**Footprint.** 4 buttons · 58 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**API.** `/api/puzzles`

**localStorage.** `lnXferCategory` · `lnXferHidden` · `lnXferText`

**Other files.** `api/puzzles.js`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1094 | `lnXferToggleBtn` | Hide ▴ | `lnXferToggle` |
| 1099 | `—` | 📋 Copy all rows | `lnXferCopy` |
| 1100 | `—` | Clear | `lnXferClear` |
| 1107 | `—` | ⬆ Send to puzzles | `lnXferSend` |

## Notes

- Small (4 buttons) and it is the bridge to vercel_fen_saver. Keep.
