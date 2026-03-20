#!/usr/bin/env python3
"""
Chess Chat with OpenAI
======================
Pass a PGN string OR a folder of .txt files, then chat interactively.

Usage:
  python chess_chat_openai.py "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6..."
  python chess_chat_openai.py ./my_games_folder
  python chess_chat_openai.py ./my_games_folder -m gpt-4o

Folder mode:
  Put .txt files in a folder. Each file can be a PGN, notes about a game,
  or any text — they all get concatenated as context.
  Example folder:
    my_games/
      game1.txt          # 1. e4 e5 2. Nf3 ...
      game1_notes.txt    # I played this against Bob, struggled in the endgame
      game2.txt          # 1. d4 d5 2. c4 ...

Then just type questions:
  > what were the critical moments?
  > was 11... Nd4 a mistake?
  > what should I study after this game?

Commands:  s = save chat,  h = history,  q = quit

Requires: pip install openai
Set: export OPENAI_API_KEY=sk-...
"""

import os
import sys
import glob
import argparse
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    print("Missing: pip install openai")
    sys.exit(1)


def load_chess_knowledge():
    """Load chess_knowledge.txt from same directory."""
    knowledge_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chess_knowledge.txt")
    try:
        with open(knowledge_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def load_folder(path):
    """Load all .txt files from a folder, concatenated with filenames as headers."""
    extensions = (".txt", ".pgn", ".md")
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(path, f"*{ext}")))
    files.sort()

    if not files:
        print(f"  No text files found in {path}")
        return None

    parts = []
    total = 0
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
            if content:
                parts.append(f"/// {os.path.basename(fpath)}\n{content}")
                total += len(content)
        except Exception:
            pass

    print(f"  Loaded {len(parts)} file(s) from {os.path.basename(path)} ({total:,} chars)")
    return "\n\n".join(parts)


def build_system_prompt(knowledge, game_context):
    """Build system prompt with chess knowledge and the game(s)."""
    parts = [
        "You are an experienced chess coach. Analyze games using Socratic questioning — "
        "help the player discover insights rather than just telling them answers.",
        "",
        "When analyzing:",
        "- Reference specific chess principles (opening theory, tactics, endgame technique)",
        "- Point out critical moments and turning points",
        "- Explain why certain moves are strong or weak",
        "- Suggest what the player should study or practice",
        "- When the player provides annotations in {curly braces} or variations in (parentheses), address those specifically",
        "- Be concrete: cite move numbers and variations",
    ]

    if knowledge:
        parts.append("")
        parts.append("CHESS KNOWLEDGE BASE:")
        parts.append(knowledge)

    parts.append("")
    parts.append("THE GAME(S) AND NOTES:")
    parts.append(game_context)

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Chess Chat with OpenAI")
    parser.add_argument("input", help="PGN string or folder path with .txt files")
    parser.add_argument("-m", "--model", default="gpt-4o-mini")
    args = parser.parse_args()

    # API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("export OPENAI_API_KEY=sk-...")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    knowledge = load_chess_knowledge()

    # Determine if input is a folder or a PGN string
    if os.path.isdir(args.input):
        game_context = load_folder(args.input)
        if not game_context:
            sys.exit(1)
        preview = f"folder: {os.path.basename(args.input)}"
    else:
        game_context = args.input
        preview = args.input[:70].replace("\n", " ") + "..."

    system_prompt = build_system_prompt(knowledge, game_context)
    messages = [{"role": "system", "content": system_prompt}]
    model = args.model

    # Banner
    print("=" * 50)
    print(f"  CHESS CHAT  |  {model}")
    print(f"  Game: {preview}")
    print("=" * 50)
    print("  Type questions about the game. s=save h=history q=quit")
    print()

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break

        if not line:
            continue

        if line.lower() == "q":
            print("bye")
            break

        if line.lower() == "s":
            save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conversations")
            os.makedirs(save_dir, exist_ok=True)
            fname = f"chess_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            fpath = os.path.join(save_dir, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(f"=== GAME ===\n{game_context}\n\n=== CONVERSATION ===\n\n")
                for m in messages:
                    if m["role"] == "system":
                        continue
                    prefix = "You" if m["role"] == "user" else "Coach"
                    f.write(f"{prefix}: {m['content']}\n\n")
            print(f"  saved {fpath}")
            continue

        if line.lower() == "h":
            for m in messages:
                if m["role"] == "system":
                    continue
                prefix = "You" if m["role"] == "user" else "Coach"
                print(f"\n{prefix}: {m['content']}")
            print()
            continue

        # Send to OpenAI
        messages.append({"role": "user", "content": line})
        try:
            print("  ...", end="", flush=True)
            resp = client.chat.completions.create(model=model, messages=messages)
            reply = resp.choices[0].message.content
            messages.append({"role": "assistant", "content": reply})
            print(f"\r  Coach: {reply}\n")
        except Exception as e:
            print(f"\n  Error: {e}")
            messages.pop()


if __name__ == "__main__":
    main()
