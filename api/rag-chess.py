# Vercel Serverless Function for Chess Coach
# Reads chess_knowledge.txt directly into system prompt (no vector DB needed)

from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request


# Read chess knowledge base once at module load time
_knowledge_path = os.path.join(os.path.dirname(__file__), '..', 'chess_knowledge.txt')
try:
    with open(_knowledge_path) as f:
        CHESS_KNOWLEDGE = f.read()
except FileNotFoundError:
    CHESS_KNOWLEDGE = ""


def call_llm(messages: list, system_prompt: str, api_key: str, model: str = "gpt-4o-mini", provider: str = "openai", web_search: bool = False) -> str:
    """Call LLM API (OpenAI or Anthropic)."""

    if provider == "anthropic":
        request_body = {
            "model": model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": messages
        }

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(request_body).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
        )

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data["content"][0]["text"]
    elif web_search and provider == "openai":
        # OpenAI Responses API with web_search tool
        openai_messages = [{"role": "system", "content": system_prompt}] + messages

        request_body = {
            "model": model,
            "tools": [{"type": "web_search"}],
            "tool_choice": "auto",
            "input": openai_messages,
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(request_body).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            # Extract text from response
            if data.get("output_text"):
                return data["output_text"]
            if data.get("output"):
                for item in data["output"]:
                    if item.get("type") == "message" and item.get("content"):
                        for content in item["content"]:
                            if content.get("type") == "output_text" and content.get("text"):
                                return content["text"]
            raise Exception("No response from web search")
    else:
        # OpenAI Chat Completions API
        openai_messages = [{"role": "system", "content": system_prompt}] + messages

        request_body = {
            "model": model,
            "max_tokens": 4096,
            "messages": openai_messages
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(request_body).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data["choices"][0]["message"]["content"]


# System prompt with full chess knowledge base baked in
CHESS_SYSTEM_PROMPT = f"""You are a chess coach with deep knowledge of chess principles and strategies.

When analyzing games or positions:
1. Reference specific chess principles when applicable - cite them explicitly
2. If analyzing a full game, cover the opening, middlegame, and endgame phases
3. If analyzing a specific move, compare it with alternatives/variations when provided
4. Explain strategic and tactical implications clearly
5. When variations are provided, explain why one line is better than another
6. Provide actionable improvement suggestions
7. Use a Socratic approach - ask thought-provoking questions to help the player discover insights
8. Recommend specific practice resources (lichess puzzles, opening explorers) when relevant

CHESS KNOWLEDGE BASE:
{CHESS_KNOWLEDGE}"""


class handler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "backend": "direct",
            "message": "Chess Coach API (full knowledge base in context)"
        }).encode())

    def do_POST(self):
        def send_json_response(status_code, data):
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
            body = json.loads(post_data.decode('utf-8'))
        except (json.JSONDecodeError, ValueError) as e:
            send_json_response(400, {"error": f"Invalid request: {str(e)}"})
            return

        query = body.get("query", "")
        messages = body.get("messages", [])
        provider = body.get("provider", "openai")
        model = body.get("model", "gpt-4o-mini")
        api_key = body.get("apiKey")
        access_code = body.get("accessCode")
        web_search = body.get("webSearch", False)

        # Resolve API key
        llm_key = None

        if api_key:
            llm_key = api_key
        elif access_code:
            valid_code = os.environ.get("ACCESS_CODE")
            if access_code != valid_code:
                send_json_response(401, {"error": "Invalid access code"})
                return
            # Use the appropriate shared key based on provider
            if provider == "anthropic":
                llm_key = os.environ.get("ANTHROPIC_API_KEY")
            else:
                llm_key = os.environ.get("OPENAI_API_KEY")
        else:
            send_json_response(400, {"error": "No API key provided"})
            return

        if not llm_key:
            send_json_response(500, {"error": f"API key not configured for {provider}"})
            return

        try:
            # Build messages — append query as user message
            augmented_messages = list(messages)
            if query:
                augmented_messages.append({"role": "user", "content": query})

            # Call LLM with full knowledge base in system prompt
            response_text = call_llm(augmented_messages, CHESS_SYSTEM_PROMPT, llm_key, model, provider, web_search)

            send_json_response(200, {
                "content": response_text,
                "query": query
            })

        except Exception as e:
            send_json_response(500, {"error": str(e)})
