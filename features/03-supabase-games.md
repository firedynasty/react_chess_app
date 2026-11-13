# Supabase game library (games / games_staging)

**Verdict: CUT — biggest single win**

Find Games by account/ECO/colour/date, load one, save it back, stage it in games_staging, transfer staging → games, and build a multi-game report.

**Entry point.** The whole block at index.html:872-950 (`Find Games`, `Load Game`, `Load Selected`, `Save to Supabase`, `Save to games_staging`, `Transfer staging → games`, `Re-analyze`, `+ Add to Report`, `Generate Report`).

**Footprint.** 17 buttons · 265 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**API.** `/api/games` · `/api/staging` · `/api/game-report`

**localStorage.** `sbReportAccessCode` · `sbReportList` · `sbSavedReports`

**Other files.** `api/games.js` · `api/staging.js` · `api/game-report.py` · `chess-rag/ (ingest/report pipeline that fed it)`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 876 | `sbFetchListBtn` | Find Games | `sbFetchGameList` |
| 879 | `sbLoadGameByIdBtn` | Load Game | `sbLoadGameByIdInput` |
| 903 | `sbLoadGameBtn` | Load Selected | `sbLoadSelectedGame` |
| 904 | `sbSaveGameBtn` | Save to Supabase | `sbSaveLoadedGame` |
| 905 | `sbStageGameBtn` | Save to games_staging | `sbStageLoadedGame` |
| 906 | `sbTransferStagedBtn` | Transfer staging → games | `sbTransferStaged` |
| 910 | `sbReanalyzeBtn` | Re-analyze | `sbReanalyze` |
| 913 | `sbAddToReportBtn` | + Add to Report | `sbAddToReport` |
| 914 | `sbGenerateReportBtn` | Generate Report (0) | `sbOpenReportModal` |
| 915 | `sbClearReportBtn` | Clear | `sbClearReportList` |
| 925 | `sbCopyGameLinkBtn` | 📋 Copy URL | `sbCopyGameLink` |
| 937 | `sbCopySectionBtn` | Copy Selected | `sbCopyReportSection` |
| 938 | `—` | Copy All | `sbCopyReport` |
| 939 | `—` | × | `sbCloseReportModal` |
| 949 | `sbRunReportBtn` | Run new report | `sbRunReport` |
| 1526 | `copyGameLinkBtnMini` | 📋 Copy URL | `sbCopyGameLink` |
| 6905 | `—` | ▶ Go to board | `sbLoadReportGameOnBoard` |

## Notes

- Deleting this retires three of your nine API endpoints and three localStorage keys — nothing else calls them (verified: `/api/games` only at index.html:6403-9692, `/api/staging` only at 7056-7161, `/api/game-report` only at 6691/6962).
- Keep `sbCopyGameLink` — the mini bar's `📋 Copy URL` (index.html:1527) calls it. Move that one function out before deleting the rest, or the quick bar breaks.
- Do NOT touch `/api/lines` or `/api/puzzles` while doing this. They are the `ln*` and `pz*` features and are still live.
- The staged deletions already in your index (api/positions.js, chess-rag/push_to_supabase.py, sql/chess_positions.sql, .github/workflows/chess-sync.yml) are the back half of this same feature. Finish the job in one commit.
- **Coupling.** The Coach Chat React component reuses this feature's access-code key:
  `localStorage.setItem('sbReportAccessCode', ...)` at `index.html:16819`. Cutting this feature
  must not delete that prompt — see [16-coach-ai.md](16-coach-ai.md).
