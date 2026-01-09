#!/usr/bin/env python3
"""
Sort PGN games by the move number where the first inaccuracy (?! or $6)
or mistake (? or $2) is detected.

Usage:
    python sort_pgn_by_annotation.py piano_game.txt
    python sort_pgn_by_annotation.py piano_game.txt > sorted.txt
"""

import re
import sys


def find_first_annotation(pgn_line):
    """
    Find the move number of the first inaccuracy (?! or $6) and
    first mistake (? or $2) in a PGN line.

    Returns: (first_inaccuracy_move, first_mistake_move)
             Returns float('inf') if annotation not found.
    """
    first_inaccuracy = float('inf')
    first_mistake = float('inf')

    # Track current move number
    current_move = 0

    # Tokenize the PGN - split by whitespace but keep structure
    # Remove comments in curly braces first
    cleaned = re.sub(r'\{[^}]*\}', ' ', pgn_line)
    # Remove variations in parentheses (simple single-level)
    cleaned = re.sub(r'\([^)]*\)', ' ', cleaned)

    tokens = cleaned.split()

    for token in tokens:
        # Check for move number (e.g., "1.", "1...", "12.")
        move_match = re.match(r'^(\d+)\.', token)
        if move_match:
            current_move = int(move_match.group(1))
            # Remove the move number prefix to check for annotation
            token = re.sub(r'^\d+\.+', '', token)

        # Check for NAG $6 (inaccuracy)
        if token == '$6':
            if current_move < first_inaccuracy:
                first_inaccuracy = current_move

        # Check for NAG $2 (mistake)
        if token == '$2':
            if current_move < first_mistake:
                first_mistake = current_move

        # Check for symbolic annotations in the token
        # Inaccuracy: ?! (but not preceded by !)
        if re.search(r'[^!]\?!|^\?!', token):
            if current_move < first_inaccuracy:
                first_inaccuracy = current_move

        # Mistake: single ? (not ?! or ??)
        # Match ? that is not followed by ! or ? and not preceded by ?
        if re.search(r'(?<!\?)\?(?![!?])', token):
            if current_move < first_mistake:
                first_mistake = current_move

    return (first_inaccuracy, first_mistake)


def sort_pgn_file(filename):
    """
    Read PGN file and sort games by first annotation move number.
    """
    games = []

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Skip header line if it doesn't look like PGN moves
            if not re.search(r'\d+\.', line):
                continue

            first_inaccuracy, first_mistake = find_first_annotation(line)
            games.append({
                'line': line,
                'first_inaccuracy': first_inaccuracy,
                'first_mistake': first_mistake
            })

    # Sort by first_inaccuracy, then first_mistake
    games.sort(key=lambda g: (g['first_inaccuracy'], g['first_mistake']))

    return games


def main():
    if len(sys.argv) < 2:
        print("Usage: python sort_pgn_by_annotation.py <pgn_file>", file=sys.stderr)
        print("Example: python sort_pgn_by_annotation.py piano_game.txt", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]

    try:
        games = sort_pgn_file(filename)

        # Print sorted games
        for game in games:
            inac = game['first_inaccuracy']
            mist = game['first_mistake']
            inac_str = str(int(inac)) if inac != float('inf') else '-'
            mist_str = str(int(mist)) if mist != float('inf') else '-'
            print(f"# First ?!: move {inac_str}, First ?: move {mist_str}")
            print(game['line'])
            print()

    except FileNotFoundError:
        print(f"Error: File '{filename}' not found", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
