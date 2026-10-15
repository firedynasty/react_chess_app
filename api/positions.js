// Vercel Serverless Function — Supabase `chess_positions` (training positions cut from games)
// Same env vars as /api/lines: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ACCESS_CODE.
// Create the table with chess-rag/sql/chess_positions.sql.
//
// Endpoints:
//   GET  /api/positions?action=list[&category=<label>][&game=<link>][&kind=blunder|idea|tactic]
//   POST /api/positions { action: "delete", id, accessCode }   -> removes one position
//   POST /api/positions { action: "save", game, category?, rows: [{ kind, pgn }], accessCode }
//        -> inserts the rows, then removes that game's OLDER rows
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
      const { action, game, kind, category } = req.query;
      if (action !== 'list') return res.status(400).json({ error: 'Unknown action. Use action=list' });
      const params = new URLSearchParams({
        select: '*',
        order: 'game.asc.nullslast,id.asc',
        limit: '1000',
      });
      if (game) params.set('game', `eq.${game}`);
      if (category) params.set('category', `eq.${category}`);
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
      const { action, id, game, category, rows, accessCode } = req.body || {};
      if (action !== 'save' && action !== 'delete') return res.status(400).json({ error: 'Unknown action. Use action=save or action=delete' });

      const validAccessCode = process.env.ACCESS_CODE;
      if (!validAccessCode || !accessCode || accessCode !== validAccessCode) {
        return res.status(401).json({ error: 'Invalid access code' });
      }
      if (action === 'delete') {
        if (!/^\d+$/.test(String(id == null ? '' : id))) return res.status(400).json({ error: 'A numeric position id is required' });
        const d = await fetch(`${url}/rest/v1/${TABLE}?id=eq.${id}`, {
          method: 'DELETE',
          headers: { ...headers, Prefer: 'return=representation' },
        });
        const gone = await d.json();
        if (!d.ok) return fail(d, gone);
        if (!gone.length) return res.status(404).json({ error: 'Position not found' });
        return res.status(200).json({ success: true, deleted: gone[0].id });
      }
      if (typeof game !== 'string' || !game.trim() || game.length > 500) {
        return res.status(400).json({ error: 'game (a link back to the full game) is required' });
      }
      if (category != null && (typeof category !== 'string' || category.length > 100)) {
        return res.status(400).json({ error: 'category must be a short text label' });
      }
      const cat = category && category.trim() ? category.trim() : null;
      if (!Array.isArray(rows) || rows.length === 0 || rows.length > MAX_ROWS) {
        return res.status(400).json({ error: `rows must be a list of 1-${MAX_ROWS} positions` });
      }

      const clean = [];
      for (const row of rows) {
        if (!row || !KINDS.includes(row.kind) ||
            typeof row.pgn !== 'string' || !row.pgn.trim() || row.pgn.length > MAX_PGN_CHARS) {
          return res.status(400).json({ error: 'each row needs kind (blunder|idea|tactic) and a pgn' });
        }
        // category only goes in when given, so a blank-category save never needs the column
        clean.push(Object.assign({ game: game.trim(), kind: row.kind, pgn: row.pgn }, cat ? { category: cat } : {}));
      }

      // Insert the new rows first, so a failure never leaves the game without positions
      const ins = await fetch(`${url}/rest/v1/${TABLE}`, {
        method: 'POST',
        headers: { ...headers, Prefer: 'return=representation' },
        body: JSON.stringify(clean),
      });
      const saved = await ins.json();
      if (!ins.ok) return fail(ins, saved);

      // Then drop this game's older rows (everything except the ones just inserted)
      const prune = new URLSearchParams({
        game: `eq.${game.trim()}`,
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
