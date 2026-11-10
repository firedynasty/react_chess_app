# Debug: why the "What went wrong" explanations stopped inventing tactics

Commit `6567c29`, 2026-11-10. Follows `42dd3fc` (explain from the punishment line)
and `0e22373` (eval bar + eval trail).

## Symptom

Explain on `6. exd5?` produced a confident, concrete, wrong story:

> ...where Black eventually plays 9... Rxe1+ on move 9, gaining material and
> shifting the evaluation significantly. ... Black is up by 5 pawns.

Nothing of the sort happens. The same notes, three lines above, said the line
ends at **Black +0.43** and never moves ¾ of a pawn the whole way.

## What it was actually fed

```
engine eval along this line: start = Black +0.60 -> 13. Qxc4 = Black +0.43  (never moves more than ¾ of a pawn)
material along this line: start = White +1 → 1… exd5 = level → 9… Rxe1+ = Black +5 → 10. Nxe1 = level
                          → 11… dxc4 = Black +1 → 12. Bxc4 = level → 12… Bxc4 = Black +3 → 13. Qxc4 = level
```

`materialTrail` sampled **every ply** and reported any change. `9… Rxe1+` means
"Black has taken the rook and White has not taken back **yet**" — one ply later
`10. Nxe1` restores it. The `+5` is the inside of an exchange, not a gain. Same
for `Black +1` at `dxc4` and `Black +3` at `Bxc4`.

So the notes contained exactly one number with a tactic attached to it, and it
was noise.

## Why the model took the bait

It was ordered to. `MM_SYSTEM` said:

> name the move in that line where the material turns, quoting the material trail

That instruction has no exit. Asked to name the move where material turns, a
model will always name one — and the only candidate on offer was `Rxe1+`. The
flat eval sat in the same prompt with no instruction attaching any weight to it,
so it lost to the number that had a story.

**This was a regression I introduced in `42dd3fc`**, fixing the opposite
failure (circular explanations: "Nf3 was bad because they replied Nf6"). That
fix worked by giving the model something concrete to point at. It gave it
something concrete *and wrong*.

## What changed

### 1. The trail drops exchanges in progress (`materialPoints`)

A value is skipped when either:

- the **next ply restores it** to the previous value (`Rxe1+` → `Nxe1`), or
- the **next ply is a capture on the same square** (`Bxd4` → `Qxd4`), which
  catches long chains where the count never returns to where it started.

Plus: a line that stops on a capture doesn't report that last value at all —
the recapture is simply unknown.

### 2. Net material is measured from *before* the flagged move

A punishment line starts the ply **after** the mistake, so a pawn the mistake
grabbed is already on the board. Reading the line's own first ply made a plain
recapture look like the opponent winning a pawn. `materialNet(b, f.fenBefore)`
compares against the real baseline.

### 3. The engine eval is declared the verdict

It is printed first, and `MM_SYSTEM` now says material snapshots are not gains,
only `net material` is, and that no explanation may claim a win the eval does
not show.

### 4. The *question* changes when there is nothing to find

`branchGain()` computes the eval swing and the net material before the call. If
the swing is under 75cp **and** nothing is netted, the ask becomes "there is no
tactic here — say what the drop costs and explain the positional damage", instead
of "name the move where it turns". The model is no longer asked for something
that isn't there.

### 5. Explain measures first

`measureForExplain()` runs the engine over the punishment line before asking, so
there is always a verdict to agree with. Previously, unless you had pressed
**Eval line** yourself, the notes read `not measured`.

## Before / after on real lines

| line | old trail | new trail | new net |
|---|---|---|---|
| `exd5 … Rxe1+ Nxe1 … dxc4 Bxc4 Bxc4 Qxc4` | `White +1 → level → Black +5 → level → Black +1 → level → Black +3 → level` | `start = White +1 → 1… exd5 = level` | unchanged (level before the move and at the end) |
| `Nxe5 Nxe5 d4 Bxd4 Qxd4 Nc6` | every rung of the chain | `start = level → 1… Nxe5 = Black +2 → 3. Qxd4 = level` | unchanged |
| `Nxe4 Nxe4 d5 d4` (piece really won) | `level → Black +1 → White +2` | `start = level → 2. Nxe4 = White +2` | White nets 2 |

The third row is the control: the filter must not eat a real gain. It doesn't.

`8. Qd1` is the other useful control — eval swing is only 7cp, but the e4 pawn
is genuinely won and kept, so `gain = 1`, the flat branch does **not** fire, and
the model is still told to walk the line. Gating on the eval alone would have
got that one wrong.

## How to re-check any of this

In the browser console, with a game loaded:

```js
const D = window.mmDebug;
const b = { plies: D.buildPlies('<base FEN>', '<san san san>'.split(' ')) };
D.materialTrail(b);                  // the snapshots
D.materialNet(b, '<fen before the mistake>');
D.branchGain(b, 'w', '<fen before the mistake>');   // { swing, gain }
```

To see the prompt without spending a call, stub `window.fetch` and call
`D.askOpenAI(f, 'test')` — `cap.messages[1].content` is everything the model sees.

## Still approximate

- `getCapturedPieces` counts against the opening array, so a promotion reads as
  a pawn captured plus a spare piece. Same convention as the main board's strip.
- A capture answered by a capture on a *different* square (a desperado, an
  in-between check that takes something else) still shows as a snapshot. The
  `net material` line and the prompt guard carry it; the trail is labelled
  `NOT gains` for exactly this reason.
- `swing < 75cp` is a guess at "flat". Easy to tune in `askOpenAI`.
