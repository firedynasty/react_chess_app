# What went wrong pane

**Verdict: KEEP**

Flags your eval drops, names the cause, walks the punishment line, shows captured material and the lead, plays out branches, and writes a note straight into the PGN.

**Entry point.** `🔍 What went wrong` (index.html:1507) → `#mmModal`.

**Footprint.** 21 buttons · 133 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**Other files.** `debug-20261110-material-trail.md` · `draft-20261110-135426-0dcff71f.md`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1506 | `mmBtn` | 🔍 What went wrong | `mmOpen` |
| 19816 | `—` | Run | `mmRun` |
| 19817 | `—` | Copy all notes | `mmCopy` |
| 19818 | `—` | Explain untagged | `mmExplainAll` |
| 19825 | `—` | × | `mmClose` |
| 20409 | `—` | ' + esc(x.label) + ' | `mmGo` |
| 20427 | `—` | ⏮ | `mmGo` |
| 20428 | `—` | ◀ | `mmStep` |
| 20429 | `—` | ▶ | `mmStep` |
| 20430 | `—` | ⏭ | `mmGo` |
| 20433 | `—` | ⇅ | `mmFlip` |
| 20441 | `—` | ' + (mmEvalBusy ? 'Getting eval…' : '📊 Eval line') + ' | `mmLineEval` |
| 20453 | `—` | Copy this FEN | `mmCopyFen` |
| 20454 | `—` | Copy snippet | `mmCopySnippet` |
| 20456 | `—` | Send to the main board | `mmToBoard` |
| 20543 | `—` | ' + (active ? '▶ Showing' : '▶ Step') + ' | `mmPlay` |
| 20546 | `—` | ' + (busy ? 'Stop' : '⏩ Play out') + ' | `mmPlayOut` |
| 20598 | `—` | ' + esc(label(f.node)) + ' | `mmJump` |
| 20604 | `—` | ' + (f.explaining ? '…' : f.explain ? 'Re-explain' : 'Explain') + ' | `mmExplain` |
| 20606 | `—` | Copy notes | `mmNote` |
| 20607 | `—` | ' + (note ? '💬 Edit note' : '💬 Comment') + ' | `mmComment` |

## Notes

- Eight of your last twenty commits are this feature. It is the newest coherent thing in the app — keep it whole.
- Its 21 buttons are internal to one modal, so it is also the cheapest feature to reason about. Leave it alone.
- `mmCopyFen` / `mmCopySnippet` / `mmCopy` / `mmNote` are four more clipboard variants — fold them into the shared three when you do `clipboard-sprawl.md`.
