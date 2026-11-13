-- Tactics / variations saved straight off the board with "Copy Var" → "Save to Supabase".
-- One row per snippet: a name you type, and the variation as a From Position PGN.
--
--   name  your label, e.g. spear, bishop-rook combo, bishop is handling the rook
--   pgn   [Variant "From Position"][FEN "..."] 1... axb3 2. Bd4 Rf5 3. axb3 Nf7
--
-- Run in: Supabase dashboard -> SQL Editor.
--
-- Name is deliberately NOT unique: saving is an append, exactly like the
-- "Append to sheet" button (name in column A, snippet in column B, new row each
-- time). Save "spear" five times and you get five rows, newest first in the list.
-- Want names to be unique instead (so ?line=<name> always means one row, and the
-- app's Replace can overwrite it)? Run this once, after clearing any duplicates:
--   alter table chess_variations add constraint chess_variations_name_key unique (name);

create table if not exists chess_variations (
  id    bigint generated always as identity primary key,
  name  text not null check (name !~ '^[0-9]+$'),  -- can't be all digits: a number means the row #
  pgn   text not null
);

create index if not exists chess_variations_name_idx on chess_variations (name);

-- RLS on with NO policies = the public anon key can't touch it; only the
-- server's service_role key (used by /api/lines) can, same as chess_lines.
alter table chess_variations enable row level security;

-- Columns are name + pgn, so /api/lines picks this table up automatically:
-- it appears in the app's table dropdown, and ?line=<name> deep-links a row.
-- No endpoint or server change is needed.
