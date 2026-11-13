// Vercel Serverless Function — `games_staging` holding table -> `games`
// Same env vars as /api/games, plus ACCESS_CODE (as /api/lines):
//   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ACCESS_CODE
//
// Save a game here when chesssync hasn't pulled it into `games` yet, then push
// the staged rows across in one go. Create the table with
// chess-rag/sql/games_staging.sql.
//
// Endpoints:
//   GET  /api/staging?action=list
//   GET  /api/staging?action=get&source=chesscom&game_id=123
//   POST /api/staging { action: "stage",   pgn, username[, source, game_id], accessCode }
//   POST /api/staging { action: "promote", accessCode }
//        copies every staged row that is not yet in `games` across, then empties staging.
//        A game `games` already has (chesssync / the daily action got there first) is
//        left as it is and its staged copy is just deleted.

const MAX_PGN_CHARS = 200000;
const COLUMNS = 'source,game_id,username,white,black,white_elo,black_elo,result,my_color,my_result,eco,time_control,termination,played_at,pgn';

function header(pgn, key) {
  const m = pgn.match(new RegExp(`\\[${key}\\s+"([^"]*)"\\]`));
  return m ? m[1] : null;
}

const elo = (v) => (v && /^\d+$/.test(v) ? parseInt(v, 10) : null);

function playedAt(pgn) {
  const date = header(pgn, 'UTCDate') || header(pgn, 'Date');
  const time = header(pgn, 'UTCTime') || '00:00:00';
  if (!date || date === '????.??.??') return null;
  const d = new Date(`${date.replace(/\./g, '-')}T${time}Z`);
  return isNaN(d) ? null : d.toISOString();
}

// chess.com carries the id in [Link], lichess in [Site]
function guessSourceAndId(pgn) {
  const link = header(pgn, 'Link') || '';
  let m = link.match(/chess\.com\/game\/(?:live|daily)\/(\d+)/);
  if (m) return { source: 'chesscom', game_id: m[1] };
  m = (header(pgn, 'Site') || '').match(/lichess\.org\/([A-Za-z0-9]{8})/);
  if (m) return { source: 'lichess', game_id: m[1] };
  return {};
}

function myColorAndResult(white, black, result, username) {
  const u = (username || '').toLowerCase();
  let color = null;
  if (white && white.toLowerCase() === u) color = 'white';
  else if (black && black.toLowerCase() === u) color = 'black';
  if (!color) return [null, null];
  if (result === '1/2-1/2') return [color, 'draw'];
  if (result === '1-0') return [color, color === 'white' ? 'win' : 'loss'];
  if (result === '0-1') return [color, color === 'white' ? 'loss' : 'win'];
  return [color, null];
}

function rowFromPgn(pgn, source, game_id, username) {
  const white = header(pgn, 'White');
  const black = header(pgn, 'Black');
  const result = header(pgn, 'Result');
  const [my_color, my_result] = myColorAndResult(white, black, result, username);
  return {
    source, game_id, username, white, black,
    white_elo: elo(header(pgn, 'WhiteElo')),
    black_elo: elo(header(pgn, 'BlackElo')),
    result, my_color, my_result,
    eco: header(pgn, 'ECO'),
    time_control: header(pgn, 'TimeControl'),
    termination: header(pgn, 'Termination'),
    played_at: playedAt(pgn),
    pgn,
  };
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return res.status(500).json({ error: 'Supabase env vars not set on server.' });
  const headers = { apikey: key, Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' };

  try {
    if (req.method === 'GET') {
      if (req.query.action === 'get') {
        const { source, game_id } = req.query;
        if (!source || !game_id) return res.status(400).json({ error: 'source and game_id required' });
        const params = new URLSearchParams({ select: '*', source: `eq.${source}`, game_id: `eq.${game_id}`, limit: '1' });
        const r = await fetch(`${url}/rest/v1/games_staging?${params}`, { headers });
        const rows = await r.json();
        if (!r.ok) return res.status(r.status).json(rows);
        if (!rows.length) return res.status(404).json({ error: 'Not in staging' });
        return res.status(200).json(rows[0]);
      }
      if (req.query.action !== 'list') return res.status(400).json({ error: 'Unknown action. Use action=list or action=get' });
      const params = new URLSearchParams({
        select: 'source,game_id,username,white,black,result,played_at,staged_at',
        order: 'staged_at.desc',
      });
      const r = await fetch(`${url}/rest/v1/games_staging?${params}`, { headers });
      return res.status(r.status).json(await r.json());
    }

    if (req.method === 'POST') {
      const { action, pgn, username, accessCode } = req.body || {};
      const validAccessCode = process.env.ACCESS_CODE;
      if (!validAccessCode || !accessCode || accessCode !== validAccessCode) {
        return res.status(401).json({ error: 'Invalid access code' });
      }

      if (action === 'stage') {
        if (!pgn || !username) return res.status(400).json({ error: 'pgn and username are required' });
        if (String(pgn).length > MAX_PGN_CHARS) return res.status(413).json({ error: 'PGN too large' });
        const guessed = guessSourceAndId(pgn);
        const source = req.body.source || guessed.source;
        const game_id = req.body.game_id || guessed.game_id;
        if (!source || !game_id) {
          return res.status(400).json({ error: 'Could not tell the source / game id from the PGN headers (no chess.com [Link] or lichess [Site])' });
        }
        const r = await fetch(`${url}/rest/v1/games_staging?on_conflict=source,game_id`, {
          method: 'POST',
          headers: { ...headers, Prefer: 'resolution=merge-duplicates,return=minimal' },
          body: JSON.stringify([rowFromPgn(String(pgn), source, String(game_id), username)]),
        });
        if (!r.ok) return res.status(r.status).json(await r.json().catch(() => ({})));
        return res.status(200).json({ success: true, source, game_id });
      }

      if (action === 'promote') {
        const g = await fetch(`${url}/rest/v1/games_staging?select=${COLUMNS}`, { headers });
        const staged = await g.json();
        if (!g.ok) return res.status(g.status).json(staged);
        if (!staged.length) return res.status(200).json({ success: true, moved: 0 });

        const ins = await fetch(`${url}/rest/v1/games?on_conflict=source,game_id`, {
          method: 'POST',
          headers: { ...headers, Prefer: 'resolution=ignore-duplicates,return=representation' },
          body: JSON.stringify(staged),
        });
        const inserted = await ins.json().catch(() => []);
        if (!ins.ok) return res.status(ins.status).json(inserted);

        // Remove only what was copied, so a game staged while this ran stays staged.
        // Matched per row on (source, game_id) -- ids are sent URL-encoded.
        let removed = 0;
        for (const row of staged) {
          const params = new URLSearchParams({ source: `eq.${row.source}`, game_id: `eq.${row.game_id}` });
          const d = await fetch(`${url}/rest/v1/games_staging?${params}`, { method: 'DELETE', headers });
          if (d.ok) removed++;
        }
        return res.status(200).json({ success: true, moved: inserted.length, alreadyThere: staged.length - inserted.length, cleared: removed });
      }

      return res.status(400).json({ error: 'Unknown action. Use action=stage or action=promote' });
    }

    return res.status(405).json({ error: 'Method not allowed' });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
