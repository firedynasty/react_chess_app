-- Training positions cut from games: one row per flagged (?/??) or commented
-- move, stored as a From Position PGN ([FEN] header + the move, its comment and
-- the next few moves). Read/written only through /api/positions.
--
-- Run in: Supabase dashboard -> SQL Editor.
--
--   kind  blunder = flagged ? / ?? (find the better move) · tactic = a ?? move whose
--         better move was forcing (capture / check / mate) — a missed tactic
--         · idea = commented move
--   category  your own label to group games, e.g. french_defense: save several games
--         with the same category and their positions cycle together
--   game  link back to the full game: https://react-chess-app-1.vercel.app/?game_id=<id>
--         (a game in your Supabase `games` table) or ...?line=<name> (a chess_lines
--         row). "Open game" loads it and jumps to the move by matching the
--         position's [FEN], so no move number is stored. NULL for loose positions.
--   pgn   From Position PGN: headers, the move, { comment }, ( variations ), a few moves

create table if not exists chess_positions (
  id        bigint generated always as identity primary key,
  kind      text not null check (kind in ('blunder', 'idea', 'tactic')),
  category  text,   -- your label for grouping games, e.g. french_defense
  game      text,
  pgn       text not null
);

-- Already created the table before `category` existed? Run just these two lines:
--   alter table chess_positions add column if not exists category text;
--   create index if not exists chess_positions_category_idx on chess_positions (category, id);
create index if not exists chess_positions_game_idx on chess_positions (game, id);
create index if not exists chess_positions_category_idx on chess_positions (category, id);

-- RLS on with NO policies = the public anon key can't touch it; only the
-- server's service_role key (used by /api/positions) can.
alter table chess_positions enable row level security;
