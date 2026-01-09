#!/usr/bin/env python3
"""
Fetch last N games from Chess.com for TTTstanley and save to a .txt file.
Adds opening comment after move 1 with color/result info.

Usage: python chess_grab_five_games.py <output_file.txt> [--number N]
"""

import requests
import re
import sys
import os
import argparse
from datetime import datetime


USERNAME = 'tttstanley'
DEFAULT_NUM_GAMES = 5


def fetch_games(username, num_games=5):
    """Fetch last N games from Chess.com API"""
    headers = {
        'User-Agent': 'Chess Game Fetcher (Python/requests)',
        'Accept': 'application/json'
    }

    games_list = []
    now = datetime.now()
    year = now.year
    month = now.month

    # Try current month first
    archive_url = f"https://api.chess.com/pub/player/{username.lower()}/games/{year}/{str(month).zfill(2)}"

    try:
        response = requests.get(archive_url, headers=headers, timeout=10)
        if response.ok:
            data = response.json()
            if 'games' in data:
                games_list.extend(data['games'])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching current month: {e}")

    # If not enough games, try previous month
    if len(games_list) < num_games:
        prev_month = month - 1
        prev_year = year
        if prev_month == 0:
            prev_month = 12
            prev_year -= 1

        prev_url = f"https://api.chess.com/pub/player/{username.lower()}/games/{prev_year}/{str(prev_month).zfill(2)}"

        try:
            response = requests.get(prev_url, headers=headers, timeout=10)
            if response.ok:
                data = response.json()
                if 'games' in data:
                    games_list.extend(data['games'])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching previous month: {e}")

    # Sort by end_time (most recent first) and take last N
    games_list.sort(key=lambda g: g.get('end_time', 0), reverse=True)
    return games_list[:num_games]


def extract_header(pgn_text, header_name):
    """Extract a header value from PGN"""
    pattern = rf'\[{header_name} "([^"]+)"\]'
    match = re.search(pattern, pgn_text)
    return match.group(1) if match else None


def extract_opening_name(pgn_text):
    """Extract opening name from ECOUrl or Opening header"""
    # First try Opening header
    opening = extract_header(pgn_text, 'Opening')
    if opening and opening != 'Unknown':
        return opening

    # Parse from ECOUrl like: https://www.chess.com/openings/Italian-Game-Giuoco-Piano
    eco_url = extract_header(pgn_text, 'ECOUrl')
    if eco_url and '/openings/' in eco_url:
        # Extract part after /openings/
        opening_part = eco_url.split('/openings/')[-1]
        # Remove move suffixes like "...4.Be2-O-O-5.O-O"
        opening_part = re.sub(r'\.\.\..*$', '', opening_part)
        opening_part = re.sub(r'-\d+\..*$', '', opening_part)
        # Replace hyphens with spaces
        opening_name = opening_part.replace('-', ' ')
        if opening_name and opening_name != 'Undefined':
            return opening_name

    return 'Unknown Opening'


def get_result_for_player(pgn_text, username):
    """Determine if username won, lost, or drew, and who the opponent was"""
    white = extract_header(pgn_text, 'White')
    black = extract_header(pgn_text, 'Black')
    result = extract_header(pgn_text, 'Result')

    username_lower = username.lower()

    if white and white.lower() == username_lower:
        color = 'white'
        opponent = black or 'unknown'
        if result == '1-0':
            outcome = 'win'
        elif result == '0-1':
            outcome = 'loss'
        else:
            outcome = 'draw'
    elif black and black.lower() == username_lower:
        color = 'black'
        opponent = white or 'unknown'
        if result == '0-1':
            outcome = 'win'
        elif result == '1-0':
            outcome = 'loss'
        else:
            outcome = 'draw'
    else:
        color = 'unknown'
        outcome = 'unknown'
        opponent = 'unknown'

    return color, outcome, opponent


def add_opening_comment(pgn_text, username):
    """Add opening comment after first move, return clean PGN without headers/clocks"""
    eco = extract_header(pgn_text, 'ECO') or '?'
    opening = extract_opening_name(pgn_text)
    color, outcome, opponent = get_result_for_player(pgn_text, username)

    # Build comment
    comment = f"{{opening: {eco} {opening}, {username} was {color} with {outcome} against {opponent}}}"

    # Extract just the moves (skip headers)
    lines = pgn_text.split('\n')
    move_lines = []

    for line in lines:
        stripped = line.strip()
        # Skip headers and empty lines
        if stripped.startswith('[') or not stripped:
            continue
        move_lines.append(stripped)

    moves_text = ' '.join(move_lines)

    # Remove clock annotations {[%clk ...]}
    moves_text = re.sub(r'\s*\{\[%clk[^\}]*\}\s*', ' ', moves_text)
    # Clean up extra whitespace
    moves_text = re.sub(r'\s+', ' ', moves_text).strip()

    # Insert comment after first move (after "1. e4" or "1. d4")
    pattern = r'^(1\.\s*\S+)'
    modified_moves = re.sub(pattern, rf'\1 {comment}', moves_text, count=1)

    return modified_moves


def main():
    parser = argparse.ArgumentParser(
        description='Fetch Chess.com games'
    )
    parser.add_argument('output_file', nargs='?', help='Output .txt file')
    parser.add_argument('--number', '-n', type=int, default=DEFAULT_NUM_GAMES,
                        help=f'Number of games to fetch (default: {DEFAULT_NUM_GAMES})')
    parser.add_argument('--user', '-u', type=str, default=USERNAME,
                        help=f'Chess.com username (default: {USERNAME})')

    args = parser.parse_args()

    if not args.output_file:
        print("Error: Need .txt file to be named")
        print(f"Usage: python {sys.argv[0]} <output_file.txt> [--number N] [--user USERNAME]")
        sys.exit(1)

    output_file = args.output_file
    num_games = args.number
    username = args.user

    # Ensure .txt extension
    if not output_file.endswith('.txt'):
        output_file += '.txt'

    # Create parent directories if needed (like mkdir -p)
    parent_dir = os.path.dirname(output_file)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    print(f"Fetching last {num_games} games for {username}...")
    games = fetch_games(username, num_games)

    if not games:
        print("No games found!")
        sys.exit(1)

    print(f"Found {len(games)} games")

    # Prepare PGN content with opening comments
    pgn_entries = []
    for i, game in enumerate(games, 1):
        if 'pgn' not in game:
            print(f"  Game {i}: No PGN available, skipping")
            continue

        pgn = game['pgn']
        modified_pgn = add_opening_comment(pgn, username)
        pgn_entries.append(modified_pgn)

        # Print summary
        eco = extract_header(pgn, 'ECO') or '?'
        opening = extract_opening_name(pgn)
        color, outcome, opponent = get_result_for_player(pgn, username)
        print(f"  Game {i}: {eco} {opening[:40]} ({color}, {outcome} vs {opponent})")

    # Append to file (or create if doesn't exist)
    mode = 'a' if os.path.exists(output_file) else 'w'
    action = 'Appending to' if mode == 'a' else 'Creating'

    with open(output_file, mode, encoding='utf-8') as f:
        if mode == 'a':
            f.write('\n\n')  # Add separator if appending
        f.write('\n\n'.join(pgn_entries))
        f.write('\n')  # Trailing newline

    print(f"\n{action} {output_file}")
    print(f"Saved {len(pgn_entries)} games")


if __name__ == "__main__":
    main()
