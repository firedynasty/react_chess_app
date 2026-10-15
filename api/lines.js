// Vercel Serverless Function — Supabase `chess_*` line tables (saved PGNs to learn from)
// Same env vars as /api/games, plus the ACCESS_CODE already used by /api/chat:
//   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ACCESS_CODE
//
// Only tables named chess_<letters/digits/underscores> are reachable, so this
// endpoint can never read or write `games`, `puzzles`, or anything else.
// Create a table with chess-rag/sql/chess_lines.sql (copy the file for more
// tables — any chess_* table with the same columns shows up automatically).
//
// Endpoints:
//   GET  /api/lines?action=tables
//   GET  /api/lines?action=list&table=chess_lines&limit=500
//   GET  /api/lines?action=get&table=chess_lines&id=12          (row # = id)
//   GET  /api/lines?action=get&table=chess_lines&name=chessable_cheesecake_1
//   POST /api/lines  { action: "save", table, name, pgn, accessCode[, replace: true] }
//                    replace:true overwrites the pgn of an existing row with that name
//                    -> writes require accessCode === process.env.ACCESS_CODE

const TABLE_RE = /^chess_[a-z0-9_]+$/;
const MAX_PGN_CHARS = 200000;

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

  try {
    if (req.method === 'GET') {
      const { action, table, id, name, limit } = req.query;

      if (action === 'tables') {
        // PostgREST publishes its schema at the API root (service_role only).
        // Offer chess_* tables that have name + pgn columns; fall back to chess_lines.
        let names = [];
        try {
          const r = await fetch(`${url}/rest/v1/`, { headers });
          const spec = await r.json();
          const defs = (spec && spec.definitions) || {};
          names = Object.keys(defs).filter(n => TABLE_RE.test(n) && defs[n].properties && defs[n].properties.name && defs[n].properties.pgn);
        } catch (e) { /* fall through to the default */ }
        if (!names.length) names = ['chess_lines'];
        return res.status(200).json(names.sort());
      }

      if (!TABLE_RE.test(table || '')) {
        return res.status(400).json({ error: 'table must be named chess_<name>' });
      }

      if (action === 'list') {
        const params = new URLSearchParams({
          select: 'id,name',
          order: 'id.desc',
          limit: String(Math.min(parseInt(limit, 10) || 500, 1000)),
        });
        const r = await fetch(`${url}/rest/v1/${table}?${params}`, { headers });
        const rows = await r.json();
        if (!r.ok) return res.status(r.status).json(rows);
        return res.status(200).json(rows);
      }

      if (action === 'get') {
        const byName = !!name && !id;
        if (!byName && !/^\d+$/.test(String(id || ''))) return res.status(400).json({ error: 'A row # (id) or a name is required' });
        const params = new URLSearchParams({ select: '*', limit: '1' });
        params.set(byName ? 'name' : 'id', `eq.${byName ? name : id}`);
        const r = await fetch(`${url}/rest/v1/${table}?${params}`, { headers });
        const rows = await r.json();
        if (!r.ok) return res.status(r.status).json(rows);
        if (!rows.length) return res.status(404).json({ error: byName ? `No row named "${name}" in ${table}` : `No row #${id} in ${table}` });
        return res.status(200).json(rows[0]);
      }

      return res.status(400).json({ error: 'Unknown action. Use action=tables, action=list, or action=get' });
    }

    if (req.method === 'POST') {
      const { action, table, name, pgn, accessCode, replace } = req.body || {};
      if (action !== 'save') return res.status(400).json({ error: 'Unknown action. Use action=save' });

      const validAccessCode = process.env.ACCESS_CODE;
      if (!validAccessCode || !accessCode || accessCode !== validAccessCode) {
        return res.status(401).json({ error: 'Invalid access code' });
      }
      if (!TABLE_RE.test(table || '')) {
        return res.status(400).json({ error: 'table must be named chess_<name>' });
      }
      if (!name || !pgn) {
        return res.status(400).json({ error: 'name and pgn are required' });
      }
      if (/^\d+$/.test(String(name).trim())) {
        return res.status(400).json({ error: 'name can\'t be all digits (a number means the row #) — e.g. chessable_cheesecake_1' });
      }
      if (String(pgn).length > MAX_PGN_CHARS) {
        return res.status(413).json({ error: 'PGN too large' });
      }

      const r = await fetch(`${url}/rest/v1/${table}${replace ? '?on_conflict=name' : ''}`, {
        method: 'POST',
        headers: { ...headers, Prefer: (replace ? 'resolution=merge-duplicates,' : '') + 'return=representation' },
        body: JSON.stringify([{ name: String(name).trim(), pgn: String(pgn) }]),
      });
      const created = await r.json();
      if (r.status === 409) return res.status(409).json({ error: `A row named "${String(name).trim()}" already exists — pick another name` });
      if (!r.ok) return res.status(r.status).json(created);
      return res.status(200).json({ success: true, row: created[0] });
    }

    return res.status(405).json({ error: 'Method not allowed' });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
