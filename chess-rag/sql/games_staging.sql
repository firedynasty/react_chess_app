-- Holding table for games saved from the app BEFORE chesssync has pulled them
-- into `games`. Read/written only through /api/staging; the "Push staged ->
-- games" button copies the rows into `games` and empties this table.
--
-- Run in: Supabase dashboard -> SQL Editor.

create table if not exists games_staging (like games including defaults);
alter table games_staging drop column if exists id;       -- keyed by (source, game_id) instead
alter table games_staging add column if not exists staged_at timestamptz not null default now();
create unique index if not exists games_staging_source_game_id on games_staging (source, game_id);

-- Same lock-down as `games`: no policies, so only the server's service_role key gets in.
alter table games_staging enable row level security;
