# Vercel Serverless Function — AI game report for a hand-picked list of games.
# Web port of chess-rag/report.py: same per-game and comparison prompts, but
# PGNs come from the Supabase `games` table instead of local raw/ files, and
# there's no tree.sqlite on the server so the historical tree stats are omitted.
#
# The client calls this once per game (action "game") and then once for the
# cross-game comparison (action "compare"), so each call stays well under the
# function timeout and the modal can fill in progressively.
#
#   POST /api/game-report { action: "game",    source, game_id, pgn?, model?, apiKey? | accessCode? }
#   POST /api/game-report { action: "compare", games: [{source, game_id, pgn?}, ...], model?, apiKey? | accessCode? }
#
# `pgn` is the browser's Stockfish-annotated copy; without it the stored PGN is used.
#
# Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY, ACCESS_CODE

from http.server import BaseHTTPRequestHandler
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request


_knowledge_path = os.path.join(os.path.dirname(__file__), '..', 'chess_knowledge.txt')
try:
    with open(_knowledge_path) as f:
        CHESS_KNOWLEDGE = f.read()
except FileNotFoundError:
    CHESS_KNOWLEDGE = ""


# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def fetch_game_row(source: str, game_id: str) -> dict | None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase env vars not set on server.")
    params = urllib.parse.urlencode({
        "select": "source,game_id,white,black,result,my_color,my_result,eco,time_control,played_at,pgn",
        "source": f"eq.{source}",
        "game_id": f"eq.{game_id}",
        "limit": "1",
    })
    req = urllib.request.Request(
        f"{url}/rest/v1/games?{params}",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req) as r:
        rows = json.loads(r.read().decode("utf-8"))
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Helpers (mirrors report.py)
# ---------------------------------------------------------------------------

def pgn_header(pgn: str, key: str) -> str:
    m = re.search(rf'\[{re.escape(key)}\s+"([^"]*)"\]', pgn)
    return m.group(1) if m else ""


def pgn_moves_only(pgn: str) -> str:
    lines = pgn.strip().split("\n")
    move_lines = [l for l in lines if l and not l.startswith("[")]
    return " ".join(move_lines).strip()


def game_summary(row: dict, pgn_override: str | None = None) -> dict:
    """report.py's game_summary(), preferring the Supabase columns over PGN headers.

    `pgn_override` is the browser's Stockfish-annotated copy, when it made one.
    """
    pgn = pgn_override or row.get("pgn") or ""
    return {
        "id":        row["game_id"],
        "source":    row["source"],
        "white":     row.get("white") or pgn_header(pgn, "White"),
        "black":     row.get("black") or pgn_header(pgn, "Black"),
        "result":    row.get("result") or pgn_header(pgn, "Result"),
        "date":      (row.get("played_at") or "")[:10] or pgn_header(pgn, "Date") or pgn_header(pgn, "EndDate"),
        "my_color":  row.get("my_color") or pgn_header(pgn, "MyColor"),
        "my_result": row.get("my_result") or pgn_header(pgn, "MyResult"),
        "opening":   pgn_header(pgn, "Opening") or row.get("eco") or pgn_header(pgn, "ECO"),
        "time_ctrl": row.get("time_control") or pgn_header(pgn, "TimeControl"),
        "url":       pgn_header(pgn, "Link") or pgn_header(pgn, "Site"),
        "pgn":       pgn,
    }


def public_meta(g: dict) -> dict:
    return {k: v for k, v in g.items() if k != "pgn"}


# ---------------------------------------------------------------------------
# Engine annotations — the PGNs are Stockfish-annotated in the browser before
# a report runs ({[%eval x]} after every move, ?/??/?! glyphs, and a
# "(... {best x})" best-line variation on mistakes). Pull the flagged moves out
# so the prompt names the real turning points instead of the LLM guessing.
# ---------------------------------------------------------------------------

_EVAL_RE = re.compile(r"\[%eval (#?-?[\d.]+)\]|^\s*(#-?\d+)\s*$")
_MOVE_NUM_RE = re.compile(r"^(\d+)(\.\.\.|\.)$")


def _parse_eval(comment: str) -> float | None:
    """Comment text -> pawns from White's view (mate = +/-100), or None."""
    m = _EVAL_RE.search(comment)
    if not m:
        return None
    v = m.group(1) or m.group(2)
    if v.startswith("#"):
        return -100.0 if v.startswith("#-") else 100.0
    return float(v)


def _fmt_eval(v: float | None) -> str:
    if v is None:
        return "?"
    if abs(v) >= 100:
        return "mate for White" if v > 0 else "mate for Black"
    return f"{v:+.2f}"


def engine_flagged_moves(pgn: str, my_color: str) -> list[str]:
    """Main-line moves carrying a ?, ?? or ?! glyph, with eval before -> after."""
    body = pgn.split("\n\n", 1)[1] if pgn.lstrip().startswith("[") and "\n\n" in pgn else pgn
    # Pair each variation with the move it follows so we can quote the best line
    best_lines: dict[int, str] = {}
    main = []
    depth, buf = 0, ""
    for ch in body:
        if ch == "(":
            if depth == 0:
                buf = ""
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            if depth == 0:
                main.append(f" \x00VAR{len(best_lines)}\x00 ")
                best_lines[len(best_lines)] = re.sub(r"\{[^}]*\}", "", buf).split()
        elif depth:
            buf += ch
        else:
            main.append(ch)
    tokens = re.findall(r"\{[^}]*\}|\x00VAR\d+\x00|\S+", "".join(main))

    flags, num, black, last_eval = [], 0, False, 0.2
    pending = None  # flagged move waiting for its eval comment / variation
    for t in tokens:
        if t.startswith("{"):
            ev = _parse_eval(t[1:-1])
            if ev is not None:
                if pending is not None and "after" not in pending:
                    pending["after"] = ev
                last_eval = ev
            continue
        if t.startswith("\x00VAR"):
            if pending is not None:
                line = best_lines[int(t[4:-1])]
                pending["best"] = " ".join(w for w in line if not _MOVE_NUM_RE.match(w))[:60]
            continue
        m = _MOVE_NUM_RE.match(t)
        if m:
            num, black = int(m.group(1)), m.group(2) == "..."
            continue
        if t in ("1-0", "0-1", "1/2-1/2", "*"):
            continue
        # A SAN move token
        if pending is not None:
            flags.append(pending)
            pending = None
        g = re.search(r"(\?\?|\?!|\?)$", t)
        if g:
            side = "black" if black else "white"
            pending = {
                "label": f"{num}{'...' if black else '.'} {t}",
                "who": "me" if side == (my_color or "").lower() else "opponent",
                "before": last_eval,
            }
        black = not black
        if not black:
            num += 1
    if pending is not None:
        flags.append(pending)

    kind = {"??": "blunder", "?": "mistake", "?!": "inaccuracy"}
    out = []
    for f in flags:
        glyph = re.search(r"(\?\?|\?!|\?)$", f["label"]).group(1)
        line = (f"- {f['label']} ({kind[glyph]} by {f['who']}): "
                f"eval {_fmt_eval(f['before'])} -> {_fmt_eval(f.get('after'))}")
        if f.get("best"):
            line += f"; engine preferred: {f['best']}"
        out.append(line)
    return out


def format_engine_section(g: dict) -> str:
    if not re.search(r"\[%eval |\{#-?\d+\}", g["pgn"]):
        return "No engine analysis available for this game."
    flags = engine_flagged_moves(g["pgn"], g["my_color"])
    if not flags:
        return "Stockfish found no inaccuracies, mistakes or blunders on either side."
    return "\n".join(flags)


# ---------------------------------------------------------------------------
# Prompts (from report.py, minus the tree-stats section)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a direct chess analyst. Be specific and concrete.
When analyzing games:
- Identify the exact moves where the advantage shifted
- Explain WHY those moves were good or bad (principles, not just engine numbers)
- Compare wins vs losses to find the pattern
- Keep it focused — no filler, no preamble
"""


def build_single_game_prompt(game: dict, knowledge: str) -> str:
    moves = pgn_moves_only(game["pgn"])
    my_color = game["my_color"] or "unknown"
    my_result = game["my_result"] or "unknown"

    ctx = ""
    if knowledge:
        ctx = f"""
## Chess Theory Reference
{knowledge[:6000]}
---
"""

    return f"""{ctx}
## Game to Analyze
- Players: {game['white']} (White) vs {game['black']} (Black)
- I played: {my_color} | Result for me: {my_result}
- Date: {game['date']} | Time control: {game['time_ctrl']}
- URL: {game['url']}

## Moves
Evals in {{[%eval x]}} are Stockfish, in pawns from White's view, after each move.
Glyphs: ?? blunder, ? mistake, ?! inaccuracy. A (...) variation is Stockfish's best line.
{moves}

## Stockfish-Flagged Moves
{format_engine_section(game)}

---
Ground every claim about who was better, and which move lost or won, in the
engine evals above. Do not invent tactics the evals don't support.
Analyze this game. Focus on:
1. The opening — did I follow good principles or deviate badly?
2. The critical turning point — what specific move(s) decided the game?
3. What I should have played instead
4. One concrete thing to improve or study based on this game
"""


def build_comparison_prompt(games: list[dict], knowledge: str) -> str:
    wins   = [g for g in games if g["my_result"] == "win"]
    losses = [g for g in games if g["my_result"] == "loss"]
    draws  = [g for g in games if g["my_result"] == "draw"]

    def game_block(g: dict) -> str:
        return (
            f"### {'Win' if g['my_result']=='win' else 'Loss' if g['my_result']=='loss' else 'Draw'}"
            f" vs {g['black'] if g['my_color']=='white' else g['white']}"
            f" ({g['date']}, {g['opening'] or 'unknown opening'})\n"
            f"{pgn_moves_only(g['pgn'])}\n"
            f"Stockfish-flagged moves:\n{format_engine_section(g)}\n"
        )

    all_blocks = "\n".join(game_block(g) for g in games)

    ctx = ""
    if knowledge:
        ctx = f"## Chess Theory Reference\n{knowledge[:4000]}\n---\n"

    # Unlike report.py's --position runs, a hand-picked list may span openings.
    return f"""{ctx}
## Games to Compare ({len(games)} total: {len(wins)} wins, {len(losses)} losses, {len(draws)} draws)
These games were hand-picked for comparison; they may or may not share an opening.

Evals in {{[%eval x]}} are Stockfish, in pawns from White's view. Ground every
claim about mistakes in the engine evals and flagged moves — don't invent tactics.

{all_blocks}

---
Compare these games and answer:
1. What did I do DIFFERENTLY in the wins vs the losses?
2. Is there a recurring mistake in the losses (specific move, pawn structure, piece placement, time use)?
3. What pattern in the wins can I replicate?
4. One concrete recommendation: what should I play, avoid, or study next?
"""


def call_openai(api_key: str, prompt: str, model: str) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1500,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class handler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
        except (json.JSONDecodeError, ValueError) as e:
            return self.send_json(400, {"error": f"Invalid request: {e}"})

        # Same key resolution as rag-chess.py: own key, or access code → shared key
        llm_key = body.get("apiKey")
        if not llm_key:
            access_code = body.get("accessCode")
            if not access_code:
                return self.send_json(400, {"error": "No API key or access code provided"})
            if access_code != os.environ.get("ACCESS_CODE"):
                return self.send_json(401, {"error": "Invalid access code"})
            llm_key = os.environ.get("OPENAI_API_KEY")
            if not llm_key:
                return self.send_json(500, {"error": "OPENAI_API_KEY not configured on server"})

        model = body.get("model") or "gpt-4o"
        action = body.get("action")

        try:
            if action == "game":
                row = fetch_game_row(body.get("source", ""), str(body.get("game_id", "")))
                if not row:
                    return self.send_json(404, {"error": "Game not found"})
                g = game_summary(row, body.get("pgn"))
                report = call_openai(llm_key, build_single_game_prompt(g, CHESS_KNOWLEDGE), model)
                return self.send_json(200, {"content": report, "game": public_meta(g)})

            if action == "compare":
                refs = body.get("games") or []
                if len(refs) < 2:
                    return self.send_json(400, {"error": "Need at least 2 games to compare"})
                games = []
                for ref in refs:
                    row = fetch_game_row(ref.get("source", ""), str(ref.get("game_id", "")))
                    if row:
                        games.append(game_summary(row, ref.get("pgn")))
                if len(games) < 2:
                    return self.send_json(404, {"error": "Fewer than 2 of the games were found"})
                report = call_openai(llm_key, build_comparison_prompt(games, CHESS_KNOWLEDGE), model)
                return self.send_json(200, {"content": report})

            return self.send_json(400, {"error": f"Unknown action: {action}"})
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            return self.send_json(502, {"error": f"Upstream HTTP {e.code}: {detail}"})
        except Exception as e:
            return self.send_json(500, {"error": str(e)})
