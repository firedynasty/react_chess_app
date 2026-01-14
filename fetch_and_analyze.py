#!/usr/bin/env python3
"""
Fetch games from Chess.com and add Stockfish variations interactively.

Usage:
    python fetch_and_analyze.py
    python fetch_and_analyze.py --user tttstanley --number 10
"""

import argparse
import chess
import chess.pgn
import chess.engine
import io
import os
import sys
import re
import requests
from datetime import datetime


# ============================================================================
# Classification Thresholds
# ============================================================================

# Thresholds in centipawns (100 cp = 1 pawn)
BLUNDER_THRESHOLD = -200  # Loss of 2+ pawns
MISTAKE_THRESHOLD = -100  # Loss of 1+ pawn
OPENING_MOVES = 8         # Skip minor errors in first N full moves


# ============================================================================
# Chess.com Fetching (from chess_grab_five_games.py)
# ============================================================================

DEFAULT_USERNAME = 'tttstanley'
DEFAULT_NUM_GAMES = 5


def fetch_games_from_chesscom(username, num_games=5):
    """Fetch last N games from Chess.com API"""
    headers = {
        'User-Agent': 'Chess Analysis Tool (Python/requests)',
        'Accept': 'application/json'
    }

    games_list = []
    now = datetime.now()
    year = now.year
    month = now.month

    print(f"Fetching games for {username}...")

    # Try current month first
    archive_url = f"https://api.chess.com/pub/player/{username.lower()}/games/{year}/{str(month).zfill(2)}"

    try:
        response = requests.get(archive_url, headers=headers, timeout=10)
        if response.ok:
            data = response.json()
            if 'games' in data:
                games_list.extend(data['games'])
                print(f"  Found {len(data['games'])} games in {year}/{month:02d}")
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching current month: {e}")

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
                    print(f"  Found {len(data['games'])} games in {prev_year}/{prev_month:02d}")
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching previous month: {e}")

    # Sort by end_time (most recent first) and take last N
    games_list.sort(key=lambda g: g.get('end_time', 0), reverse=True)
    return games_list[:num_games]


def extract_header(pgn_text, header_name):
    """Extract a header value from PGN"""
    pattern = rf'\[{header_name} "([^"]+)"\]'
    match = re.search(pattern, pgn_text)
    return match.group(1) if match else None


def get_game_summary(pgn_text, username):
    """Get a one-line summary of a game"""
    white = extract_header(pgn_text, 'White') or '?'
    black = extract_header(pgn_text, 'Black') or '?'
    result = extract_header(pgn_text, 'Result') or '?'
    date = extract_header(pgn_text, 'Date') or '?'
    eco = extract_header(pgn_text, 'ECO') or ''
    opening = extract_header(pgn_text, 'Opening') or ''
    time_control = extract_header(pgn_text, 'TimeControl') or ''

    # Determine if user won/lost/drew
    username_lower = username.lower()
    if white.lower() == username_lower:
        color = 'W'
        outcome = 'Win' if result == '1-0' else ('Loss' if result == '0-1' else 'Draw')
    elif black.lower() == username_lower:
        color = 'B'
        outcome = 'Win' if result == '0-1' else ('Loss' if result == '1-0' else 'Draw')
    else:
        color = '?'
        outcome = result

    opening_short = opening[:30] + '...' if len(opening) > 30 else opening

    return f"{white} vs {black} | {outcome}({color}) | {eco} {opening_short} | {time_control}"


# ============================================================================
# Stockfish Analysis (from stockfish_add_variation.py)
# ============================================================================

def find_stockfish():
    """Find Stockfish executable in common locations"""
    common_paths = [
        "/usr/local/bin/stockfish",
        "/usr/bin/stockfish",
        "/opt/homebrew/bin/stockfish",
        os.path.expanduser("~/stockfish/stockfish"),
        os.path.expanduser("~/bin/stockfish"),
        "stockfish",
    ]

    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
        if path == "stockfish":
            try:
                import shutil
                found = shutil.which("stockfish")
                if found:
                    return found
            except:
                pass
    return None


def parse_move_location(move_str):
    """Parse move location string like '12.' or '12...'"""
    move_str = move_str.strip()
    match = re.match(r'^(\d+)(\.{1,3})$', move_str)
    if not match:
        raise ValueError(f"Invalid format: '{move_str}'. Use '12.' for White or '12...' for Black")

    move_number = int(match.group(1))
    dots = match.group(2)
    is_black_move = len(dots) == 3

    return move_number, is_black_move


def get_position_at_move(game, move_number, is_black_move):
    """Get the board position BEFORE the specified move is played."""
    board = game.board()
    node = game

    target_ply = (move_number - 1) * 2
    if is_black_move:
        target_ply += 1

    current_ply = 0

    while node.variations:
        next_node = node.variation(0)

        if current_ply == target_ply:
            return board, next_node

        board.push(next_node.move)
        node = next_node
        current_ply += 1

    raise ValueError(f"Move {move_number}{'...' if is_black_move else '.'} not found in game")


def analyze_position(board, engine, num_lines=3, depth=18):
    """Analyze position with Stockfish and return top moves."""
    info_list = engine.analyse(
        board,
        chess.engine.Limit(depth=depth),
        multipv=num_lines
    )

    results = []
    for info in info_list:
        if 'pv' in info and len(info['pv']) > 0:
            move = info['pv'][0]
            score = info.get('score', None)
            pv = info['pv'][:5]

            if score:
                if score.is_mate():
                    mate_in = score.relative.mate()
                    score_str = f"#{'+'if mate_in > 0 else ''}{mate_in}"
                else:
                    cp = score.relative.score() / 100.0
                    score_str = f"{cp:+.2f}"
            else:
                score_str = "?"

            results.append({
                'move': move,
                'score': score_str,
                'pv': pv,
                'san': board.san(move)
            })

    return results


def format_variation_line(board, pv, move_number, is_black_move):
    """Format a variation line as PGN."""
    temp_board = board.copy()
    parts = []

    for i, move in enumerate(pv):
        current_move_num = move_number + (i + (1 if is_black_move else 0)) // 2
        is_black = (i + (1 if is_black_move else 0)) % 2 == 1

        san = temp_board.san(move)

        if i == 0:
            if is_black_move:
                parts.append(f"{move_number}... {san}")
            else:
                parts.append(f"{move_number}. {san}")
        elif not is_black:
            parts.append(f"{current_move_num}. {san}")
        else:
            parts.append(san)

        temp_board.push(move)

    return ' '.join(parts)


def clean_pgn_for_parsing(pgn_text):
    """
    Clean PGN for python-chess parsing.
    python-chess handles chess.com format fine, so we just do minimal cleanup.
    """
    # python-chess can parse chess.com PGN directly (handles 1... format and clock annotations)
    # Just return the raw PGN - it works!
    return pgn_text


def clean_pgn_for_output(pgn_text):
    """
    Clean PGN for final output - remove clock annotations and non-essential headers.
    """
    # Remove clock annotations { [%clk 0:04:59.8] } (note: spaces inside braces)
    cleaned = re.sub(r'\s*\{\s*\[%clk[^\]]*\]\s*\}\s*', ' ', pgn_text)

    # Remove excessive whitespace
    cleaned = re.sub(r' +', ' ', cleaned)
    cleaned = re.sub(r'\n +', '\n', cleaned)

    # Remove non-essential headers (keep core ones)
    essential_headers = ['Event', 'Site', 'Date', 'Round', 'White', 'Black', 'Result',
                         'WhiteElo', 'BlackElo', 'ECO', 'Opening', 'TimeControl']

    lines = cleaned.split('\n')
    output_lines = []
    in_headers = True

    for line in lines:
        if line.startswith('['):
            # Check if it's an essential header
            for header in essential_headers:
                if line.startswith(f'[{header} '):
                    output_lines.append(line)
                    break
        else:
            if in_headers and line.strip() == '':
                in_headers = False
                output_lines.append('')  # Keep one blank line after headers
            elif not in_headers:
                output_lines.append(line)

    return '\n'.join(output_lines).strip()


def classify_move(eval_before_cp, eval_after_cp, move_number, is_black_move):
    """
    Classify a move based on centipawn loss.

    Args:
        eval_before_cp: Evaluation before move (centipawns, from moving side's perspective)
        eval_after_cp: Evaluation after move (centipawns, from moving side's perspective)
        move_number: Full move number (1, 2, 3...)
        is_black_move: Whether this is Black's move

    Returns:
        tuple: (classification, loss_in_pawns) or (None, 0)
        classification is 'BLUNDER', 'MISTAKE', or None
    """
    swing = eval_after_cp - eval_before_cp  # Negative = lost advantage
    loss_pawns = abs(swing) / 100.0

    # Opening filter: skip minor errors in first N moves
    # Only flag blunders (2+ pawns) in opening
    if move_number <= OPENING_MOVES and swing > BLUNDER_THRESHOLD:
        return None, 0

    # Classify by centipawn loss
    if swing <= BLUNDER_THRESHOLD:
        return 'BLUNDER', loss_pawns
    elif swing <= MISTAKE_THRESHOLD:
        return 'MISTAKE', loss_pawns

    return None, 0


def add_variation_at_move(game, board, target_node, alt_moves, move_number, is_black_move):
    """Add Stockfish variations to the game tree."""
    parent_node = target_node.parent

    variations_added = 0
    for alt in alt_moves:
        var_node = parent_node.add_variation(alt['move'])
        var_node.comment = f"Stockfish: {alt['score']}"

        temp_board = board.copy()
        temp_board.push(alt['move'])
        current_var_node = var_node

        for continuation_move in alt['pv'][1:]:
            if continuation_move in temp_board.legal_moves:
                current_var_node = current_var_node.add_variation(continuation_move)
                temp_board.push(continuation_move)

        variations_added += 1

    return variations_added


def count_moves(game):
    """Count total moves in the main line."""
    count = 0
    node = game
    while node.variations:
        node = node.variation(0)
        count += 1
    return count


def auto_analyze_game(game, engine, depth=18):
    """
    Automatically analyze all moves and return blunders/mistakes.

    Returns:
        list of dicts with move info and classification
    """
    board = game.board()
    errors = []

    print("\nAnalyzing all moves...")

    for node in game.mainline():
        move = node.move
        moving_side = board.turn

        # Calculate move number and notation
        ply = board.ply()
        full_move_num = (ply // 2) + 1
        is_black = (ply % 2 == 1)

        # Get eval and best move BEFORE the move is made
        info_before = engine.analyse(board, chess.engine.Limit(depth=depth))
        eval_before = info_before['score'].white().score(mate_score=10000)
        best_move_uci = info_before.get('pv', [None])[0]

        # Get best move in SAN notation while board is still in pre-move state
        best_san = board.san(best_move_uci) if best_move_uci else '?'

        # Make move
        san = board.san(move)
        board.push(move)

        # Get eval after move
        info_after = engine.analyse(board, chess.engine.Limit(depth=depth))
        eval_after = info_after['score'].white().score(mate_score=10000)

        # Flip for Black's perspective
        if moving_side == chess.BLACK:
            eval_before_perspective = -eval_before
            eval_after_perspective = -eval_after
        else:
            eval_before_perspective = eval_before
            eval_after_perspective = eval_after

        # Classify
        classification, loss = classify_move(
            eval_before_perspective, eval_after_perspective,
            full_move_num, is_black
        )

        if classification:
            move_notation = f"{full_move_num}{'...' if is_black else '.'}"

            errors.append({
                'notation': move_notation,
                'played': san,
                'classification': classification,
                'loss': loss,
                'eval_before': eval_before_perspective / 100,
                'eval_after': eval_after_perspective / 100,
                'best_move': best_san
            })

            color = '\033[91m' if classification == 'BLUNDER' else '\033[93m'
            reset = '\033[0m'
            print(f"  {color}{move_notation} {san} - {classification} (lost {loss:.2f} pawns){reset}")
            print(f"    Stockfish best: {best_san} [{eval_before_perspective/100:+.2f}]")

    return errors


# ============================================================================
# Interactive Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Fetch Chess.com games and add Stockfish variations')
    parser.add_argument('--user', '-u', type=str, default=DEFAULT_USERNAME,
                        help=f'Chess.com username (default: {DEFAULT_USERNAME})')
    parser.add_argument('--number', '-n', type=int, default=DEFAULT_NUM_GAMES,
                        help=f'Number of games to fetch (default: {DEFAULT_NUM_GAMES})')
    parser.add_argument('--depth', '-d', type=int, default=18,
                        help='Stockfish search depth (default: 18)')
    parser.add_argument('--lines', '-l', type=int, default=1,
                        help='Number of alternative lines (default: 1)')
    parser.add_argument('--auto', '-a', action='store_true',
                        help='Auto-analyze all moves for blunders/mistakes')

    args = parser.parse_args()

    # Find Stockfish first
    stockfish_path = find_stockfish()
    if not stockfish_path:
        print("ERROR: Stockfish not found!")
        print("Install with: brew install stockfish (macOS) or apt install stockfish (Linux)")
        sys.exit(1)

    print(f"Using Stockfish: {stockfish_path}")
    print()

    # Fetch games
    games = fetch_games_from_chesscom(args.user, args.number)

    if not games:
        print("No games found!")
        sys.exit(1)

    print(f"\nFound {len(games)} games:\n")

    # Display game list
    valid_games = []
    for i, game in enumerate(games):
        if 'pgn' in game:
            summary = get_game_summary(game['pgn'], args.user)
            print(f"  {i + 1}. {summary}")
            valid_games.append(game)
        else:
            print(f"  {i + 1}. (No PGN available)")

    if not valid_games:
        print("No games with PGN available!")
        sys.exit(1)

    # Select game
    print()
    while True:
        try:
            choice = input(f"Select game (1-{len(valid_games)}): ").strip()
            game_idx = int(choice) - 1
            if 0 <= game_idx < len(valid_games):
                break
            print(f"Please enter a number between 1 and {len(valid_games)}")
        except ValueError:
            print("Please enter a valid number")

    selected_game = valid_games[game_idx]
    pgn_text = selected_game['pgn']

    # Clean and parse PGN
    clean_pgn = clean_pgn_for_parsing(pgn_text)
    pgn_io = io.StringIO(clean_pgn)
    game = chess.pgn.read_game(pgn_io)

    if not game:
        print("Error parsing PGN!")
        sys.exit(1)

    total_moves = count_moves(game)
    total_move_numbers = (total_moves + 1) // 2

    print(f"\nGame loaded: {total_moves} half-moves ({total_move_numbers} full moves)")
    print()

    # Print the moves for reference
    exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
    moves_only = game.accept(exporter)
    print("Moves:")
    print(moves_only[:500] + ('...' if len(moves_only) > 500 else ''))
    print()

    # Start Stockfish engine
    print("Starting Stockfish...")
    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)

    try:
        # Auto-analyze mode
        if args.auto:
            print("\n" + "=" * 60)
            print("AUTO-ANALYSIS MODE")
            print("=" * 60)

            # Re-parse game
            pgn_io = io.StringIO(clean_pgn)
            game = chess.pgn.read_game(pgn_io)

            errors = auto_analyze_game(game, engine, args.depth)

            # Summary
            print("\n" + "=" * 60)
            blunders = sum(1 for e in errors if e['classification'] == 'BLUNDER')
            mistakes = sum(1 for e in errors if e['classification'] == 'MISTAKE')
            print(f"SUMMARY: {blunders} blunder(s), {mistakes} mistake(s)")
            print("=" * 60)

            if errors:
                print("\nErrors found:")
                for e in errors:
                    color = '\033[91m' if e['classification'] == 'BLUNDER' else '\033[93m'
                    reset = '\033[0m'
                    print(f"  {color}{e['notation']} {e['played']}{reset} - {e['classification']} "
                          f"(lost {e['loss']:.2f} pawns, best: {e['best_move']})")

            return  # finally block will quit engine

        # Interactive loop for adding variations
        while True:
            print("-" * 60)
            move_input = input("\nEnter move to analyze (e.g., '12.' or '12...') or 'done' to finish: ").strip()

            if move_input.lower() in ('done', 'quit', 'exit', 'q', ''):
                break

            try:
                move_number, is_black_move = parse_move_location(move_input)

                # Re-parse game to get fresh tree (in case we've modified it)
                pgn_io = io.StringIO(clean_pgn)
                game = chess.pgn.read_game(pgn_io)

                board, target_node = get_position_at_move(game, move_number, is_black_move)
                played_san = board.san(target_node.move)

                print(f"\nAnalyzing position before {move_number}{'...' if is_black_move else '.'} {played_san}")
                print(f"Depth: {args.depth}")

                # Analyze - fetch extra line in case played move is best
                alternatives = analyze_position(board, engine, args.lines + 1, args.depth)

                # Get eval before (from first alternative)
                eval_before_str = alternatives[0]['score']
                try:
                    if eval_before_str.startswith('#'):
                        eval_before_cp = 10000 if '+' in eval_before_str else -10000
                    else:
                        eval_before_cp = int(float(eval_before_str) * 100)
                except:
                    eval_before_cp = 0

                # Get eval after played move
                board_after = board.copy()
                board_after.push(target_node.move)
                info_after = engine.analyse(board_after, chess.engine.Limit(depth=args.depth))
                eval_after_cp = info_after['score'].white().score(mate_score=10000)

                # Flip for black's perspective
                if is_black_move:
                    eval_before_perspective = -eval_before_cp
                    eval_after_perspective = -eval_after_cp
                else:
                    eval_before_perspective = eval_before_cp
                    eval_after_perspective = eval_after_cp

                # Classify the played move
                classification, loss = classify_move(
                    eval_before_perspective, eval_after_perspective,
                    move_number, is_black_move
                )

                # Display classification if applicable
                if classification:
                    color = '\033[91m' if classification == 'BLUNDER' else '\033[93m'
                    reset = '\033[0m'
                    print(f"\n{color}>>> {classification}: lost {loss:.2f} pawns{reset}")

                # Filter to only alternatives (not the played move), limit to args.lines
                alt_moves = [alt for alt in alternatives if alt['move'] != target_node.move][:args.lines]

                print(f"\nStockfish best: [{alternatives[0]['score']}] {format_variation_line(board, alternatives[0]['pv'], move_number, is_black_move)}")
                if alternatives[0]['move'] == target_node.move:
                    print("  ^ You played the best move!")

                # Add variations
                added = add_variation_at_move(game, board, target_node, alt_moves, move_number, is_black_move)

                if added > 0:
                    print(f"\nAdded {added} variation(s)")

                    # Update clean_pgn with new variations
                    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
                    clean_pgn = game.accept(exporter)
                else:
                    print("\nPlayed move was the best - no variations added")

            except ValueError as e:
                print(f"Error: {e}")
            except Exception as e:
                print(f"Error: {e}")

    finally:
        engine.quit()

    # Final output
    print("\n" + "=" * 60)
    print("FINAL PGN WITH VARIATIONS:")
    print("=" * 60 + "\n")

    # Re-parse and export final PGN
    pgn_io = io.StringIO(clean_pgn)
    game = chess.pgn.read_game(pgn_io)
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    final_pgn = game.accept(exporter)

    # Clean up clock annotations and non-essential headers for display
    final_pgn = clean_pgn_for_output(final_pgn)

    print(final_pgn)

    # Save option
    print()
    save = input("Save to file? (enter filename or press Enter to skip): ").strip()
    if save:
        if not save.endswith('.pgn'):
            save += '.pgn'
        with open(save, 'w') as f:
            f.write(final_pgn)
        print(f"Saved to: {save}")


if __name__ == "__main__":
    main()
