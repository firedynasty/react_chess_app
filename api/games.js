// Vercel Serverless Function — Supabase `games` table proxy
// Keeps SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY server-side. service_role
// is required (not the anon key) because RLS on `games` has no
// anon/authenticated policies -- see chess-rag/push_to_supabase.py.
//
// Set in Vercel dashboard -> Settings -> Environment Variables:
//   SUPABASE_URL = https://xxxx.supabase.co
//   SUPABASE_SERVICE_ROLE_KEY = your-service-role-key
//
// Endpoints:
//   GET  /api/games?action=list&source=chesscom&username=X&limit=100
//   GET  /api/games?action=get&source=chesscom&game_id=123
//   POST /api/games   { action: "save", source, game_id, pgn }

const LIST_COLUMNS =
  'id,source,game_id,username,white,black,white_elo,black_elo,result,my_color,my_result,eco,time_control,played_at';

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
      const { action, source, username, game_id, limit } = req.query;

      if (action === 'list') {
        const params = new URLSearchParams({
          select: LIST_COLUMNS,
          order: 'played_at.desc.nullslast',
          limit: limit || '100',
        });
        if (source) params.set('source', `eq.${source}`);
        if (username) params.set('username', `eq.${username}`);
        const r = await fetch(`${url}/rest/v1/games?${params}`, { headers });
        const rows = await r.json();
        return res.status(r.ok ? 200 : r.status).json(rows);
      }

      if (action === 'get') {
        if (!source || !game_id) return res.status(400).json({ error: 'source and game_id required' });
        const params = new URLSearchParams({ select: '*', source: `eq.${source}`, game_id: `eq.${game_id}`, limit: '1' });
        const r = await fetch(`${url}/rest/v1/games?${params}`, { headers });
        const rows = await r.json();
        if (!r.ok) return res.status(r.status).json(rows);
        if (!rows.length) return res.status(404).json({ error: 'Game not found' });
        return res.status(200).json(rows[0]);
      }

      return res.status(400).json({ error: 'Unknown action. Use action=list or action=get' });
    }

    if (req.method === 'POST') {
      const { action, source, game_id, pgn } = req.body || {};
      if (action !== 'save') return res.status(400).json({ error: 'Unknown action. Use action=save' });
      if (!source || !game_id || !pgn) {
        return res.status(400).json({ error: 'source, game_id, and pgn are required' });
      }

      const params = new URLSearchParams({ source: `eq.${source}`, game_id: `eq.${game_id}` });
      const r = await fetch(`${url}/rest/v1/games?${params}`, {
        method: 'PATCH',
        headers: { ...headers, Prefer: 'return=representation' },
        body: JSON.stringify({ pgn }),
      });
      const updated = await r.json();
      if (!r.ok) return res.status(r.status).json(updated);
      if (!Array.isArray(updated) || updated.length === 0) {
        return res.status(404).json({ error: 'Game not found (no row matched source/game_id)' });
      }
      return res.status(200).json({ success: true });
    }

    return res.status(405).json({ error: 'Method not allowed' });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
