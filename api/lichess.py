# Vercel Serverless Function — prototype for retrieving PGNs from Lichess.
#
# GET /api/lichess?gameId=<id-or-full-lichess-url>
#   Exports a single game's PGN. Works today.
#
# GET /api/lichess?username=<name>&max=<n>
#   Attempts to export a user's recent games as PGN via Lichess's documented
#   bulk endpoint (GET https://lichess.org/api/games/user/{username}).
#   As of this writing that endpoint 404s upstream for every account tested
#   (including well-known ones, not just new/empty accounts) — tracked at
#   lichess-org/api#667, same issue chess-rag/ingest.py's fetch_lichess_games
#   stub is blocked on. Left wired up so it starts working automatically
#   once Lichess fixes it; until then it surfaces the upstream error.

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import re
import urllib.request
import urllib.error


GAME_ID_RE = re.compile(r"[A-Za-z0-9]{8}")


def extract_game_id(raw: str) -> str | None:
    """
    Pull an 8-char Lichess game ID out of either a bare ID or a full game
    URL (e.g. "https://lichess.org/QaLO5QFkjZaR" -> "QaLO5QFk").

    Lichess game URLs are sometimes longer than 8 chars (extra trailing
    chars, or a "/black"·"/white" perspective suffix); Lichess itself
    redirects those to the canonical 8-char form, so we mirror that here.
    """
    tail = raw.rsplit("lichess.org/", 1)[-1]
    tail = tail.split("/")[0].split("?")[0]
    match = GAME_ID_RE.match(tail)
    return match.group(0) if match else None


def fetch_game_pgn(game_id: str) -> str:
    """GET https://lichess.org/game/export/{gameId} -> raw PGN text."""
    url = f"https://lichess.org/game/export/{game_id}?evals=false&clocks=false"
    req = urllib.request.Request(url, headers={"Accept": "application/x-chess-pgn"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def fetch_user_games_pgn(username: str, max_games: int) -> str:
    """
    GET https://lichess.org/api/games/user/{username} -> concatenated PGN text.

    See module docstring — currently broken upstream (api#667).
    """
    url = (
        f"https://lichess.org/api/games/user/{username}"
        f"?max={max_games}&sort=dateDesc"
    )
    req = urllib.request.Request(url, headers={"Accept": "application/x-chess-pgn"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


class handler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        game_id_raw = query.get("gameId", [None])[0]
        username = query.get("username", [None])[0]

        try:
            max_games = int(query.get("max", ["10"])[0])
        except ValueError:
            self._send_json(400, {"error": "max must be an integer"})
            return

        if game_id_raw:
            game_id = extract_game_id(game_id_raw)
            if not game_id:
                self._send_json(
                    400, {"error": f"Could not parse a game ID from '{game_id_raw}'"}
                )
                return
            try:
                pgn = fetch_game_pgn(game_id)
            except urllib.error.HTTPError as e:
                self._send_json(
                    e.code, {"error": f"Lichess returned {e.code} for game {game_id}"}
                )
                return
            except urllib.error.URLError as e:
                self._send_json(502, {"error": f"Could not reach Lichess: {e.reason}"})
                return
            self._send_json(200, {"gameId": game_id, "pgn": pgn})
            return

        if username:
            try:
                pgn = fetch_user_games_pgn(username, max_games)
            except urllib.error.HTTPError as e:
                self._send_json(
                    e.code,
                    {
                        "error": f"Lichess returned {e.code} for user '{username}'",
                        "note": (
                            "The bulk /api/games/user endpoint is currently broken "
                            "upstream (lichess-org/api#667) — reproduced against "
                            "known accounts too, not just this one. Use ?gameId= "
                            "for single games in the meantime."
                        ),
                    },
                )
                return
            except urllib.error.URLError as e:
                self._send_json(502, {"error": f"Could not reach Lichess: {e.reason}"})
                return
            self._send_json(200, {"username": username, "pgn": pgn})
            return

        self._send_json(
            400,
            {
                "error": "Pass ?gameId=<id or lichess.org URL> or ?username=<name>&max=<n>",
                "example": "/api/lichess?gameId=QaLO5QFkjZaR",
            },
        )
