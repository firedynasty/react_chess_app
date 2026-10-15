-- Training positions cut from games: one row per flagged (?/??) or commented
-- move, stored as a From Position PGN ([FEN] header + the move, its comment and
-- the next few moves). Read/written only through /api/positions.
--
-- Run in: Supabase dashboard -> SQL Editor.
--
--   kind  blunder = flagged ? / ?? (find the better move) · idea = commented move
--         · tactic = reserved for puzzle positions you add yourself (Lichess ones)
--   game  link back to the full game: https://react-chess-app-1.vercel.app/?game_id=<id>
--         (a game in your Supabase `games` table) or ...?line=<name> (a chess_lines
--         row). "Open game" loads it and jumps to the move by matching the
--         position's [FEN], so no move number is stored. NULL for loose positions.
--   pgn   From Position PGN: headers, the move, { comment }, ( variations ), a few moves

create table if not exists chess_positions (
  id    bigint generated always as identity primary key,
  kind  text not null check (kind in ('blunder', 'idea', 'tactic')),
  game  text,
  pgn   text not null
);

create index if not exists chess_positions_game_idx on chess_positions (game, id);

-- RLS on with NO policies = the public anon key can't touch it; only the
-- server's service_role key (used by /api/positions) can.
alter table chess_positions enable row level security;
