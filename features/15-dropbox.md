# Dropbox (PGN load, report save, print-list sync)

**Verdict: KEEP, consolidate**

PKCE sign-in, browse/search Dropbox, load a .pgn to the board, save reports, and save/load the print list JSON.

**Entry point.** `Dropbox PGN` (866) · `DB Login`/`DB Files`/`DB Logout` (1173-1175) · `💾 DB Save` (1039) · `☁ Save/Load to Dropbox` (18976-18977).

**Footprint.** 11 buttons · 171 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**API.** `/api/dropbox-config`

**localStorage.** `dropbox_code_verifier` · `chessPrintDropboxPath`

**Other files.** `api/dropbox-config.js` · `summary0211_dropbox.txt`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 865 | `dbPgnBtn` | Dropbox PGN | `dropboxPgnButtonClick @3266` |
| 1038 | `dbSaveBtn` | 💾 DB Save **(hidden)** | `dropboxSaveReport @3268` |
| 1172 | `dbLoginBtn` | DB Login | `dropboxSignIn @3263` |
| 1173 | `dbFilesBtn` | DB Files **(hidden)** | `openDropboxSidebar @3264` |
| 1174 | `dbLogoutBtn` | DB Logout **(hidden)** | `dropboxSignOut @3265` |
| 2056 | `dropboxSidebarLogout` | Sign out | `dropboxSignOut @3267` |
| 2057 | `closeDropboxSidebar` | × *(~inherited)* | `closeDropboxSidebar @3270` |
| 2061 | `dropboxPasteBtn` | Paste | `async @3276` |
| 2062 | `dropboxSearchBtn` | Search | `function @3286` |
| 2068 | `dropboxSaveConfirmBtn` | Save | `dropboxConfirmSave @3271` |
| 2072 | `dropboxBackBtn` | ← Back to results | `function @3295` |

## Notes

- One auth flow, four scattered entry points: `dbPgnBtn`, the `DB Login`/`DB Files`/`DB Logout` trio, `dbSaveBtn`, and the print-list pair.
- Keep the plumbing (index.html:2753-3316, cleanly sectioned already) and collapse the entry points to one `Dropbox ▾`.
