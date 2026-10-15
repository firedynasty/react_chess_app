// Vercel Serverless Function — Supabase `chess_positions` (training positions cut from games)
// Same env vars as /api/lines: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ACCESS_CODE.
// Create the table with chess-rag/sql/chess_positions.sql.
//
// Endpoints:
//   GET  /api/positions?action=list[&game=<link>][&kind=blunder|idea|tactic]
//   POST /api/positions { action: "save", game, rows: [{ kind, pgn }], accessCode }
//        -> inserts the rows, then removes that game's OLDER blunder/idea rows
//           (re-saving a game refreshes its positions). Needs accessCode.

const TABLE = 'chess_positions';
const KINDS = ['blunder', 'idea', 'tactic'];
const MAX_PGN_CHARS = 20000;
const MAX_ROWS = 300;

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    return res.status(500).json({ error: 'Supabase env vars not set on server.' });
  }
  const headers = { apikey: key, Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' };
  const fail = (r, body) => res.status(r.status).json({ error: (body && (body.message || body.hint)) || `Supabase error (HTTP ${r.status})` });

  try {
    if (req.method === 'GET') {
      const { action, game, kind } = req.query;
      if (action !== 'list') return res.status(400).json({ error: 'Unknown action. Use action=list' });
      const params = new URLSearchParams({
        select: '*',
        order: 'game.asc.nullslast,id.asc',
        limit: '1000',
      });
      if (game) params.set('game', `eq.${game}`);
      if (kind) {
        if (!KINDS.includes(kind)) return res.status(400).json({ error: 'kind must be blunder, idea or tactic' });
        params.set('kind', `eq.${kind}`);
      }
      const r = await fetch(`${url}/rest/v1/${TABLE}?${params}`, { headers });
      const rows = await r.json();
      if (!r.ok) return fail(r, rows);
      return res.status(200).json(rows);
    }

    if (req.method === 'POST') {
      const { action, game, rows, accessCode } = req.body || {};
      if (action !== 'save') return res.status(400).json({ error: 'Unknown action. Use action=save' });

      const validAccessCode = process.env.ACCESS_CODE;
      if (!validAccessCode || !accessCode || accessCode !== validAccessCode) {
        return res.status(401).json({ error: 'Invalid access code' });
      }
      if (typeof game !== 'string' || !game.trim() || game.length > 500) {
        return res.status(400).json({ error: 'game (a link back to the full game) is required' });
      }
      if (!Array.isArray(rows) || rows.length === 0 || rows.length > MAX_ROWS) {
        return res.status(400).json({ error: `rows must be a list of 1-${MAX_ROWS} positions` });
      }

      const clean = [];
      for (const row of rows) {
        if (!row || !KINDS.includes(row.kind) ||
            typeof row.pgn !== 'string' || !row.pgn.trim() || row.pgn.length > MAX_PGN_CHARS) {
          return res.status(400).json({ error: 'each row needs kind (blunder|idea|tactic) and a pgn' });
        }
        clean.push({ game: game.trim(), kind: row.kind, pgn: row.pgn });
      }

      // Insert the new rows first, so a failure never leaves the game without positions
      const ins = await fetch(`${url}/rest/v1/${TABLE}`, {
        method: 'POST',
        headers: { ...headers, Prefer: 'return=representation' },
        body: JSON.stringify(clean),
      });
      const saved = await ins.json();
      if (!ins.ok) return fail(ins, saved);

      // Then drop this game's older generated rows (everything except the ones just inserted)
      const prune = new URLSearchParams({
        game: `eq.${game.trim()}`,
        kind: 'in.(blunder,idea)',
        id: `not.in.(${saved.map(r => r.id).join(',')})`,
      });
      const del = await fetch(`${url}/rest/v1/${TABLE}?${prune}`, {
        method: 'DELETE',
        headers: { ...headers, Prefer: 'return=representation' },
      });
      const removed = await del.json();
      if (!del.ok) return fail(del, removed);

      return res.status(200).json({ success: true, saved: saved.length, removed: removed.length });
    }

    return res.status(405).json({ error: 'Method not allowed' });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
