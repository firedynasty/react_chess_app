# Supabase game library (games / games_staging) — REMOVED

**Verdict: REMOVED.** Kept as the record of what went, so the links from
[README.md](README.md), [HISTORY.md](HISTORY.md), [BUTTONS.md](BUTTONS.md),
[duplicate-controls.md](duplicate-controls.md), [clipboard-sprawl.md](clipboard-sprawl.md) and
[16-coach-ai.md](16-coach-ai.md) still resolve. `git log -- api/games.js` is the archive.

Find Games by account/ECO/colour/date, load one onto the board, save it back, stage it in
`games_staging`, transfer staging → games, re-analyze it, and build a multi-game AI report. All of
it is gone: 17 buttons, three API endpoints, two localStorage keys, the whole `?game_id=` deep
link, and 1,128 lines out of `index.html`.

This was step 3 of the cut order in [README.md](README.md) — the biggest single win in the
inventory.

## What was removed

| what | where it was |
|---|---|
| the account/ECO/colour/date toolbar, the game + staged dropdowns, both report rows, `#sbReportList`, `#sbStatus` and the `#sbGameLink` deep-link line | `index.html:864-920` |
| `#sbReportModal` — the report reader, its access-code / API-key / model row and `Run new report` | `index.html:927-951` |
| `LOAD / SAVE GAMES FROM SUPABASE` — 41 functions, incl. the multi-game report and the `games_staging` half | `index.html:5762-6573` |
| `RE-ANALYZE & SAVE` — `sbReanalyze`, `sbAnnotatePgn` and 3 helpers, plus the `REANALYZE_*` thresholds | `index.html:6677-6894` |
| `copyGameLinkBtnMini` "📋 Copy URL" in the mini bar | `index.html:1510` |
| the Supabase-game reset at the top of `applyPgnStringToBoard` | `index.html:4483-4487` |
| `lnBoardPgn`'s stored-header branch | `index.html:4840-4841` |
| `lnCurrentGameLink`'s `?game_id=` branch | `index.html:5109` |
| `supabaseLoadedGame` in `PGN_TAB_KEYS`, its reset, and the three `sbRefreshGameLink` calls | `index.html:4485, 14799, 14878, 14893, 14905` |
| the game link `buildChatText` appended to Copy Chat | `index.html:15905-15906` |
| `myColorGuess`'s `my_color` branch | `index.html:19259-19260` |
| `/api/games` · `/api/staging` · `/api/game-report` | `api/games.js` · `api/staging.js` · `api/game-report.py` |
| the `supabase-games` RULES pattern | `features/extract_buttons.py` |

All line numbers are pre-removal.

**localStorage gone with it.** `sbReportList` · `sbSavedReports`. Nothing migrates these; a browser
that still holds them just carries two dead keys.

**No env var is orphaned.** `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ACCESS_CODE` and
`OPENAI_API_KEY` are all still read by `/api/lines`, `/api/puzzles`, `/api/chat` and
`/api/rag-chess`.

## Behaviour that went with it

- **The `?game_id=` deep link is dead.** `?game_id=<id>`, the bare `?<id>` form, `&source=` and
  `&ply=` all did nothing but drive this loader. `/?line=` (and `&table=`) is the only deep link
  left — see [04-supabase-lines.md](04-supabase-lines.md).
- **The mini bar's `📋 Copy URL` went too**, against this file's earlier advice to keep
  `sbCopyGameLink`. That advice assumed a game could still be loaded from Supabase. It cannot:
  `window.supabaseLoadedGame` had exactly one writer, inside the deleted section, so the button
  could only ever have reported *"No Supabase game loaded"*. `sbCurrentMainlinePly`,
  `sbJumpToMainlinePly`, `sbBuildGameLink`, `sbGetGameLink` and `sbGetOpponentName` went with it.
- **`myColorGuess`** ([10-mistake-hop.md](10-mistake-hop.md)) no longer gets the `my_color` column;
  it falls back to `board2`'s orientation, which was already its second choice.
- **`lnBoardPgn`** ([04-supabase-lines.md](04-supabase-lines.md)) no longer gets the row's stored
  `[Event]`/`[White]`/… block; it falls back to `#pgnInput` / `window.currentLoadedPgn`, which was
  already its second choice. Same for `lnCurrentGameLink`, now the PGN's `[Link "…"]` header only.
- **Copy Chat** no longer appends `Game link: …`. The chess.com / Lichess game details it pulls
  from the `#game-dropdown` are untouched.

## What it did NOT take

- **`sbReportAccessCode` stays.** The name is this feature's, the key is not: `Save board PGN`,
  `AI Comments`, Coach Chat's *Use Stanley's Key* and the mistake explainer all read and write it
  (`index.html:4704`, `4708`, `4867`, `5374`, `5685`, `5688`, `14969`, `18942`, `18945` —
  post-removal lines). [16-coach-ai.md](16-coach-ai.md) now owns it. Only the
  `#sbReportAccessCode` **input** in the report modal went.
- **`AI COMMENTS`** (`aiCommentKeyMoves`, `graftAiComments`) sat between the two deleted sections
  and is coach-ai's, not this feature's. Untouched.
- **The Google Sheets game picker** (`gnSignInBtn` / `gnRecentBtn`) lived inside the same panel,
  between the deep-link row and the report modal. Untouched —
  [14-sheets-drive.md](14-sheets-drive.md).
- `/api/lines`, `/api/puzzles`, `/api/chat`, `/api/rag-chess` and the `chess_*` / `puzzles` tables.
  `lnPost`, `lnCopyText`, `showToast`, `extractPgnHeaderBlock`, `uciListToSan` and
  `applyPgnStringToBoard` are shared and were left alone.
- **`chess-rag/`** — the offline ingest/report pipeline that filled `games` is still in the repo,
  as are its `sql/games_staging.sql` and the Supabase tables themselves. Nothing in the page reads
  them any more. Retiring the pipeline and dropping the tables is a separate decision.

## Verification

`extract_buttons.py --check` — all 6 inline script blocks parse. `extract_buttons.py` — 297
buttons down to 280, nothing `unclassified`. No `sb[A-Z]` identifier remains in `index.html`
except the `sbReportAccessCode` reads and writes above, and no reference to `/api/games`,
`/api/staging` or `/api/game-report` remains anywhere outside this inventory and `chess-rag/`.
The page loads in Chrome with no new console errors.
