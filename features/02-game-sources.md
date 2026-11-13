# chess.com / Lichess game fetchers

**Verdict: CUT (keep one)**

Fetch a player's recent games from chess.com or Lichess into a dropdown, then load one to the board.

**Entry point.** `📥 Fetch Games` (chess.com, index.html:785), `🔗 Open Game` (index.html:796), `📥 Fetch Games` (Lichess, index.html:805).

**Footprint.** 3 buttons · 13 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**Other files.** `chess_grab_five_games.py` · `chesscom_analyzer.py` · `fetch_and_analyze.py` · `prototypes/get_recent_games.py`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 785 | `fetch-games-btn` | 📥 Fetch Games | `fetchChesscomGames` |
| 796 | `open-game-btn` | 🔗 Open Game | `openChesscomGameById` |
| 805 | `fetch-lichess-btn` | 📥 Fetch Games | `fetchLichessGames` |

## Notes

- Two identically-labelled `📥 Fetch Games` buttons sit 20 lines apart. At minimum, label them.
- Your working note says games arrive by paste → Load to Board. If that holds, both fetchers go and `api/lichess.py` (already orphaned) goes with them.
- Cut the Lichess one first: `api/lichess.py` documents that the upstream bulk endpoint 404s, so the fetcher cannot work today anyway.
