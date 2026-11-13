# Coach Chat + AI → PGN

**Verdict: KEEP, cut the extra buttons**

A RAG-backed chess coach chat (ChatGPT or Anthropic), AI comments on key moves, save the chat as a Google Doc, and merge an AI-written line into the PGN.

**Entry point.** `💬 Coach Chat` (1515 and 1566) · `AI → PGN` (1511) → `#chessCoachChatModal`, `#coachPgnModal`.

**Footprint.** 21 buttons · 52 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**API.** `/api/chat` · `/api/rag-chess`

**Other files.** `chess_chat_openai.py` · `create_rag_from_text.py` · `chess_knowledge.txt` · `rag_chess/` · `chess-rag/`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 1510 | `coachpgn-btn` | AI → PGN | `openCoachPgnModal` |
| 1514 | `—` | 💬 Coach Chat | `openChessCoachChatModal` |
| 1565 | `—` | 💬 Coach Chat | `openChessCoachChatModal` |
| 1742 | `—` | ✕ | `getElementById` |
| 1750 | `—` | Merge into PGN | `coachPgnMerge` |
| 1751 | `coachPgnLineBtn` | Single line: ON | `coachPgnToggleLine` |
| 1752 | `—` | Clear | `coachPgnClear` |
| 1756 | `coachPgnCopyBtn` | Copy PGN | `coachPgnCopy` |
| 15859 | `—` | ✕ | `closeChessCoachChatModal` |
| 16726 | `—` | window.closeChessCoachChatModal && window.closeChessCoachChatModal()} *(jsx)* | `—` |
| 16739 | `—` | setAiProvider('ChatGPT')} style={{ ...styles.providerBtn, ...(aiProvid *(jsx)* | `—` |
| 16748 | `—` | setAiProvider('Anthropic')} style={{ ...styles.providerBtn, ...(aiProv *(jsx)* | `—` |
| 16770 | `—` | { const code = prompt("Enter access code for Stanley's key:"); if (cod *(jsx)* *(~inherited)* | `—` |
| 16816 | `—` | 🤖 Analyze with Chess Coach *(jsx)* *(~inherited)* | `—` |
| 16825 | `aiCommentsBtn` | window.aiCommentKeyMoves && window.aiCommentKeyMoves()} style={{ ...st *(jsx)* | `—` |
| 16835 | `—` | 🎯 Ask Coach About Selected Move *(jsx)* *(~inherited)* | `—` |
| 16844 | `—` | 📋 Retrieve Prompt *(jsx)* *(~inherited)* | `—` |
| 16853 | `—` | 🔍 Reanalyze with Higher Model *(jsx)* *(~inherited)* | `—` |
| 16863 | `—` | Copy Chat *(jsx)* *(~inherited)* | `—` |
| 16871 | `—` | { setMessages([]); setChatEnabled(false); }} style={{ ...styles.button *(jsx)* *(~inherited)* | `—` |
| 16936 | `—` | Send *(jsx)* *(~inherited)* | `—` |

## Notes

- `💬 Coach Chat` is two buttons calling one function (1515 mini bar, 1566 old row).
- Inside the React modal: `🤖 Analyze with Chess Coach`, `🎯 Ask Coach About Selected Move`, `📋 Retrieve Prompt`, `🔍 Reanalyze with Higher Model`, `Copy Chat`, `Send`, a clear, and a provider pair. Six ways to ask one question.
- The `/api/rag-chess` + `chess_knowledge.txt` side is the only non-trivial backend you still run. Keep it, prune its buttons.
- **Coupling.** The access-code prompt inside the React block writes `sbReportAccessCode`
  (`index.html:16819`), a key owned by [03-supabase-games.md](03-supabase-games.md). When that
  feature is cut, this prompt needs its own key, or Coach Chat loses its auth.
- The whole `<script type="text/babel">` block (`index.html:15912` to roughly `17000`) is this one
  component. `extract_buttons.py` assigns every button in that range here for that reason.
