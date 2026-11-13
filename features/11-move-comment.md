# Move comments + coach bubbles

**Verdict: KEEP**

Write a comment on the move you are standing on, show/hide comment bubbles, paste a comment in from the clipboard.

**Entry point.** `💬 + Comment` (index.html:1498) → `#moveCommentModal`; `⭐` (1494 and 1565) toggles bubbles.

**Footprint.** 10 buttons · 40 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**localStorage.** `coachBubblesOn`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1267 | `—` | Insert Comment | `insertPastedComment` |
| 1271 | `—` | 📋 Paste from Clipboard | `readText, then, getElementById` |
| 1275 | `—` | Clear | `getElementById` |
| 1289 | `—` | ✕ | `closeMoveCommentModal` |
| 1293 | `—` | Save | `saveMoveComment` |
| 1294 | `—` | 📋 Paste | `readText, then, getElementById, trim` |
| 1295 | `—` | Clear | `getElementById, getElementById, focus` |
| 1493 | `coachNoteBtnMini` | ⭐ | `toggleCoachBubbles` |
| 1497 | `addCommentBtn` | 💬 + Comment | `openMoveCommentModal` |
| 1564 | `coachNoteBtn` | ⭐ | `toggleCoachBubbles` |

## Notes

- The `⭐` bubble toggle exists twice (index.html:1494 mini bar, index.html:1565 old row) — same handler, two buttons.
- Comments living in the PGN `{...}` is the right call; it keeps this feature independent of every backend.
