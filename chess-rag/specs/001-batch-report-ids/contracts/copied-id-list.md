# Contract: Copied ID List → `report.py` CLI arguments

This is the one interface this feature creates: a text contract between what `tree_viewer.html`'s new copy actions place on the clipboard and what `report.py` accepts as command-line arguments. There is no network/API contract — this is a local static page and a local CLI script, connected only via the user's clipboard and terminal paste.

## Producer: `tree_viewer.html` (`copyAllIds()`, `copySelectedIds()`)

- **Output**: A single string written to `navigator.clipboard`.
- **Format**: Zero or more game IDs, each an opaque numeric-string token (e.g. `174186131000`), separated by exactly one space (`' '`) character. No leading/trailing whitespace, no newlines, no other characters.
- **Ordering**: Stable, matches the order the games are listed in the current view.
- **Uniqueness**: No ID appears more than once, even if the source list contains a duplicate game entry.
- **Empty case**: `copySelectedIds()` with zero checked games does not write to the clipboard at all (leaves prior clipboard contents untouched) and instead surfaces a user-facing message.

## Consumer: `report.py` (`main()`, `parser.add_argument("game_ids", nargs="*", ...)`)

- **Input**: Positional CLI arguments, one token per game ID, exactly matching argparse's default whitespace-splitting behavior for a pasted, space-separated string.
- **Preconditions already enforced by `report.py`** (unchanged by this feature):
  - At least one game ID (or `--position`) must be provided, else it exits with an error (`report.py:352`).
  - Each ID must resolve to a loadable PGN via `load_pgn(gid)`; unresolvable IDs are silently skipped (`report.py:362-366`).
- **Behavior triggered by 2+ valid IDs**: writes one `<id>.md` per game plus one `comparison.md` (wins vs. losses summary) — unchanged, already exists (`report.py:404-450`).

## Compatibility

Because the producer format (bare space-separated tokens) is exactly what the consumer already parses via `nargs="*"` positional arguments, no adapter/translation step is needed. This contract is satisfied purely by the producer-side format rules above — verified manually per `quickstart.md`.
