# Google Sheets picker + Drive Docs

**Verdict: CUT the write/table half**

Sign in with Google, pick a Sheet, read games out of it (read mode) or write the board's game into it (write mode); plus an editable CSV table with row navigation and per-cell copy.

**Entry point.** `Sheets ▾` (1493) · `Recent Sheets ▾` (931) · `Browse Games` (1973) · `Sign In` (1974) → `#gdrive-picker-modal`.

**Footprint.** 22 buttons · 454 lines of `index.html` match the owning pattern (see `extract_buttons.py` RULES)

**Other files.** `features/google-drive-sheets-loader.html`

## Buttons

| line | id | label | handler |
|---:|---|---|---|
| 929 | `gnSignInBtn` | Sign in with Google | `gdriveSignIn` |
| 930 | `gnRecentBtn` | Recent Sheets ▾ | `gdriveOpenPicker` |
| 1492 | `—` | Sheets ▾ | `gdriveOpenPicker` |
| 1597 | `gdriveRowUp` | ↑ Prev Row | `function @17694` |
| 1598 | `gdriveRowDown` | Next Row ↓ | `function @17700` |
| 1602 | `gdriveRowCopyBtn` | Copy | `function @17708` |
| 1918 | `—` | ✕ | `getElementById` |
| 1970 | `—` | Copy | `gdriveCopyAll` |
| 1971 | `—` | Clear | `gdriveClear` |
| 1972 | `gdrive-browse-btn` | Browse Games | `gdriveOpenPicker` |
| 1973 | `gdrive-auth-btn` | Sign In | `gdriveSignIn` |
| 1998 | `—` | Save Row | `gdriveSaveRow` |
| 1999 | `—` | Replace Row | `gdriveReplaceRow` |
| 2000 | `—` | Clear Inputs | `getElementById, getElementById, getElementById` |
| 2009 | `gdrive-picker-back-btn` | Back | `function @17454` |
| 2010 | `—` | × | `gdriveClosePicker` |
| 2014 | `gdrive-picker-search-btn` | Search | `function @17435` |
| 2015 | `gdrive-picker-recent-btn` | Recent | `function @17450` |
| 2027 | `gdrive-picker-read-mode` | Read | `function @17438` |
| 2028 | `gdrive-picker-write-mode` | Write | `function @17442` |
| 2042 | `gdrive-picker-use-board` | Use current board | `gdrivePickerUseCurrentBoard @17445` |
| 2043 | `gdrive-picker-append` | Append to sheet | `function @17287` |

## Notes

- 450 lines of index.html touch `gdrive` — the single largest feature footprint in the file.
- Your working note says the table row-loading side is not something you will use. That is `gdrive-csv-table`, `gdriveSelectedRow`, `gdriveRenderSheet`, `gdriveSaveRow`, `gdriveReplaceRow`, `gdrive-cell-input`, `gdriveCopyCell`, `gdriveRowUp`, `gdriveRowDown`, `gdriveRowCopyBtn`, `#gdriveRowLinkModal` and `#gdrive-picker-write-panel`.
- Keep read mode: `gdriveSignIn`, `gdriveOpenPicker`, `gdrivePickerListFiles`, `gdrivePickerRenderCards`, `gdriveLoadSpreadsheet`, `gdriveClosePicker`.
- This is a two-commit cut: first delete write mode and the `Read`/`Write` toggle (2028-2029), then the table area.
