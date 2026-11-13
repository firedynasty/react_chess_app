# Dropbox (PGN load, report save, print-list sync) — REMOVED

**Verdict: REMOVED.** Kept as the record of what went, so the links from
[README.md](README.md), [HISTORY.md](HISTORY.md) and [duplicate-controls.md](duplicate-controls.md)
still resolve. `git log -- api/dropbox-config.js` is the archive.

PKCE sign-in, browse/search Dropbox, load a `.pgn` to the board, save reports, and save/load the
print list JSON. All of it is gone: 11 buttons across four features, the auth plumbing, both
modals, the print-list sync, and the endpoint.

## What was removed

| what | where it was |
|---|---|
| `DROPBOX INTEGRATION (OAuth PKCE + File Operations)` — 18 functions, 564 lines | `index.html:2745-3308` |
| File-browser sidebar `#dropboxSidebar` + the Save Report As row | `index.html:2043-2071` |
| `#dropboxSidebar` mobile CSS override | `index.html:102-104` |
| `dbPgnBtn` "Dropbox PGN" | `index.html:864` |
| `dbSaveBtn` "💾 DB Save" *(hidden)* | `index.html:1037` |
| `dbLoginBtn` / `dbFilesBtn` / `dbLogoutBtn` | `index.html:1165-1167` |
| `dropboxSidebarLogout` · `closeDropboxSidebar` · `dropboxPasteBtn` · `dropboxSearchBtn` · `dropboxSaveConfirmBtn` · `dropboxBackBtn` | inside the sidebar |
| print-list sync: `ppDbxSave` / `ppDbxLoad` / `dbxPath` / `dbxReady` / `dbxMeta` / `dbxArg` / `ppDbxPathChanged`, `DBX_PATH_KEY`, `DBX_DEFAULT`, `dbxRev`, `dbxForce` | `index.html:19198-19288` |
| `☁ Save to Dropbox` / `☁ Load from Dropbox (replaces)` + the `#ppDbxPath` input | `index.html:18888-18893` |
| the per-game print path written on load from Supabase | `index.html:9805-9816` |
| `/api/dropbox-config` | `api/dropbox-config.js` |
| the `dropbox` RULES pattern | `extract_buttons.py` |

All line numbers are pre-removal.

**localStorage / sessionStorage gone with it.** `dropbox_code_verifier` · `chessPrintDropboxPath` ·
`dropbox_token` (sessionStorage). Nothing migrates these; a browser that still holds them just
carries two dead keys.

**Env var now unused.** `REACT_APP_DROPBOX_APP_KEY` on Vercel — the only thing that read it was
`/api/dropbox-config`. Pull it when convenient; nothing breaks either way.

## What it did NOT take

- **The print list still round-trips off this browser** — `⬇ Export JSON` and
  `⬆ Load JSON (replaces)` are untouched, so the list is a file you keep, not a Dropbox object.
  Only the one-click cloud path went. See [12-print-cards.md](12-print-cards.md).
- `generateCodeVerifier` / `generateCodeChallenge` went with the section: they were Dropbox's own
  PKCE helpers, called only from `dropboxSignIn`. **Google's auth has its own** and is unaffected.
- `applyPgnStringToBoard`, `showToast`, `applyLoaded`, `LINE_KEY` and the rest of the print-list
  IIFE are shared and were left alone.
- `window.isReportEditMode` is read elsewhere; only Dropbox's read of it went.
- The standalone pages `textReformatter.html`, `documentation/textviewer.html` and
  `react-chat-report-viewer/textviewer.html` have their own Dropbox code and still reference
  `/api/dropbox-config`. **`index.html` never loaded them**, and removing the endpoint breaks
  their sign-in. They are not in this inventory (see README's non-feature cleanup); decide on them
  separately.

## Verification

`extract_buttons.py --check` — all 6 inline script blocks parse. No `dropbox`, `dbx` or `db*Btn`
identifier remains in `index.html`; the only surviving mention of the word is one comment about
`vercel_fen_saver`, a **different** app that does still keep Dropbox as its source of truth.
