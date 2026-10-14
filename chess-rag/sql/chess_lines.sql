-- Saved PGN lines to learn from (Chessable exports, annotated games like
-- cheesecake_31827.pgn, opening lines). Read/written only through /api/lines.
--
-- Run in: Supabase dashboard -> SQL Editor.
-- A row is addressed by its `id` (a number, e.g. ?line=12) OR its unique
-- `name` (e.g. ?line=chessable_cheesecake_1). Names can't be all digits, so
-- a number always means the id.
--
-- Want another table (e.g. chess_chessable)? Copy this file, change the
-- table name — it must start with chess_ — and run it. It appears in the
-- app's table dropdown automatically; no code change needed.
-- (Already ran an earlier version of this file? It's empty — `drop table
-- chess_lines;` first, then run this.)

create table if not exists chess_lines (
  id    bigint generated always as identity primary key,
  name  text not null unique check (name !~ '^[0-9]+$'),  -- e.g. chessable_cheesecake_1
  pgn   text not null    -- full PGN: headers, { comments }, ( variations )
);

-- RLS on with NO policies = the public anon key can't touch it; only the
-- server's service_role key (used by /api/lines) can, same as `games`.
alter table chess_lines enable row level security;
