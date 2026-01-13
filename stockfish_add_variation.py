#!/usr/bin/env python3
"""
Stockfish Variation Adder
Analyzes a PGN at a specific move and adds Stockfish-suggested variations.

Usage:
    python stockfish_add_variation.py <pgn_file_or_string> --move "12." --lines 3
    python stockfish_add_variation.py <pgn_file_or_string> --move "12..." --lines 2

    --move "12."   = White's 12th move
    --move "12..." = Black's 12th move
    --lines N      = Number of alternative lines to add (default: 3)
    --depth D      = Stockfish search depth (default: 18)
"""

import argparse
import chess
import chess.pgn
import chess.engine
import io
import os
import sys
import re


def find_stockfish():
    """Find Stockfish executable in common locations"""
    common_paths = [
        "/usr/local/bin/stockfish",
        "/usr/bin/stockfish",
        "/opt/homebrew/bin/stockfish",
        os.path.expanduser("~/stockfish/stockfish"),
        os.path.expanduser("~/bin/stockfish"),
        "stockfish",  # Try PATH
    ]

    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
        # Try running it from PATH
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
    """
    Parse move location string like "12." or "12..."

    Returns:
        (move_number, is_black_move)
        e.g., "12." -> (12, False)
              "12..." -> (12, True)
    """
    move_str = move_str.strip()

    # Match patterns like "12." or "12..."
    match = re.match(r'^(\d+)(\.{1,3})$', move_str)
    if not match:
        raise ValueError(f"Invalid move format: '{move_str}'. Use '12.' for White or '12...' for Black")

    move_number = int(match.group(1))
    dots = match.group(2)
    is_black_move = len(dots) == 3  # "..." means black's move

    return move_number, is_black_move


def get_position_at_move(game, move_number, is_black_move):
    """
    Get the board position BEFORE the specified move is played.

    Args:
        game: chess.pgn.Game object
        move_number: The move number (1-indexed)
        is_black_move: True if we want Black's move position

    Returns:
        (board, node) - Board at position, and the node of the move to replace
    """
    board = game.board()
    node = game

    # Calculate the ply (half-move) index
    # Move 1. e4 is ply 0, 1... e5 is ply 1
    # Move 12. is ply 22 (12-1)*2 = 22
    # Move 12... is ply 23
    target_ply = (move_number - 1) * 2
    if is_black_move:
        target_ply += 1

    current_ply = 0

    while node.variations:
        next_node = node.variation(0)  # Follow main line

        if current_ply == target_ply:
            # We're at the position BEFORE the target move
            # Return the board and the node containing the move
            return board, next_node

        board.push(next_node.move)
        node = next_node
        current_ply += 1

    raise ValueError(f"Move {move_number}{'...' if is_black_move else '.'} not found in game")


def analyze_position(board, engine, num_lines=3, depth=18):
    """
    Analyze position with Stockfish and return top moves.

    Returns:
        List of (move, score, pv) tuples
    """
    # Get multiple principal variations
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
            pv = info['pv'][:5]  # First 5 moves of the line

            # Format score
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
    """
    Format a variation line as PGN.

    Args:
        board: Board at start of variation
        pv: List of moves (principal variation)
        move_number: Starting move number
        is_black_move: True if variation starts with Black's move
    """
    temp_board = board.copy()
    parts = []

    for i, move in enumerate(pv):
        current_move_num = move_number + (i + (1 if is_black_move else 0)) // 2
        is_black = (i + (1 if is_black_move else 0)) % 2 == 1

        san = temp_board.san(move)

        if i == 0:
            # First move always gets move number
            if is_black_move:
                parts.append(f"{move_number}... {san}")
            else:
                parts.append(f"{move_number}. {san}")
        elif not is_black:
            # White's move after first
            parts.append(f"{current_move_num}. {san}")
        else:
            # Black's move (no number needed unless first)
            parts.append(san)

        temp_board.push(move)

    return ' '.join(parts)


def add_variations_to_pgn(pgn_string, move_location, num_lines=3, depth=18, stockfish_path=None):
    """
    Add Stockfish variations at specified move location.

    Args:
        pgn_string: PGN text
        move_location: String like "12." or "12..."
        num_lines: Number of alternative lines
        depth: Stockfish search depth
        stockfish_path: Path to Stockfish executable

    Returns:
        Modified PGN string with variations
    """
    # Parse move location
    move_number, is_black_move = parse_move_location(move_location)

    # Find Stockfish
    if not stockfish_path:
        stockfish_path = find_stockfish()

    if not stockfish_path:
        raise RuntimeError(
            "Stockfish not found. Install it with:\n"
            "  macOS: brew install stockfish\n"
            "  Ubuntu: sudo apt install stockfish\n"
            "Or specify path with --stockfish-path"
        )

    # Parse PGN
    pgn_io = io.StringIO(pgn_string)
    game = chess.pgn.read_game(pgn_io)

    if not game:
        raise ValueError("Could not parse PGN")

    # Get position at the specified move
    board, target_node = get_position_at_move(game, move_number, is_black_move)

    # The actual move played
    played_move = target_node.move
    played_san = board.san(played_move)

    print(f"\nAnalyzing position before {move_number}{'...' if is_black_move else '.'} {played_san}")
    print(f"FEN: {board.fen()}")
    print(f"Searching depth {depth} for {num_lines} lines...\n")

    # Analyze with Stockfish
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        alternatives = analyze_position(board, engine, num_lines, depth)

    # Display results
    print("Stockfish analysis:")
    for i, alt in enumerate(alternatives, 1):
        line_str = format_variation_line(board, alt['pv'], move_number, is_black_move)
        print(f"  {i}. [{alt['score']}] {line_str}")

    # Find which alternatives are different from the played move
    variation_lines = []
    for alt in alternatives:
        if alt['move'] != played_move:
            variation_lines.append(alt)

    if not variation_lines:
        print("\nThe played move was the best move! No variations to add.")
        return pgn_string

    print(f"\nAdding {len(variation_lines)} variation(s) to PGN...")

    # Add variations to the game tree
    parent_node = target_node.parent

    for alt in variation_lines:
        # Create variation starting from parent
        var_node = parent_node.add_variation(alt['move'])
        var_node.comment = f"Stockfish: {alt['score']}"

        # Add rest of the PV as continuation
        temp_board = board.copy()
        temp_board.push(alt['move'])
        current_var_node = var_node

        for continuation_move in alt['pv'][1:]:
            if continuation_move in temp_board.legal_moves:
                current_var_node = current_var_node.add_variation(continuation_move)
                temp_board.push(continuation_move)

    # Export modified PGN
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    modified_pgn = game.accept(exporter)

    return modified_pgn


def clean_pgn_format(pgn_string):
    """
    Clean PGN format - handles non-standard formats like '1. e4 1... e5'
    """
    # Remove redundant black move numbers like "1... e5" -> just keep the move
    # Standard PGN is "1. e4 e5" not "1. e4 1... e5"

    # Pattern: digit followed by "..." - remove the number part but keep the move
    cleaned = re.sub(r'\d+\.\.\.\s*', '', pgn_string)

    # Clean up multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)

    return cleaned.strip()


def main():
    parser = argparse.ArgumentParser(
        description='Add Stockfish variations to a PGN at a specific move',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    # Analyze White's 12th move
    python stockfish_add_variation.py game.pgn --move "12."

    # Analyze Black's 8th move with 5 alternatives at depth 20
    python stockfish_add_variation.py game.pgn --move "8..." --lines 5 --depth 20

    # Use inline PGN
    python stockfish_add_variation.py "1. e4 e5 2. Nf3 Nc6" --move "2."
        '''
    )

    parser.add_argument('pgn', help='PGN file path or PGN string')
    parser.add_argument('--move', '-m', required=True,
                        help='Move location: "12." for White\'s 12th, "12..." for Black\'s 12th')
    parser.add_argument('--lines', '-l', type=int, default=3,
                        help='Number of alternative lines (default: 3)')
    parser.add_argument('--depth', '-d', type=int, default=18,
                        help='Stockfish search depth (default: 18)')
    parser.add_argument('--stockfish-path', '-s',
                        help='Path to Stockfish executable')
    parser.add_argument('--output', '-o',
                        help='Output file (default: print to stdout)')

    args = parser.parse_args()

    # Read PGN
    if os.path.isfile(args.pgn):
        with open(args.pgn, 'r') as f:
            pgn_string = f.read()
    else:
        pgn_string = args.pgn

    # Clean PGN format if needed
    if re.search(r'\d+\.\.\.', pgn_string):
        print("Detected non-standard PGN format, cleaning...")
        pgn_string = clean_pgn_format(pgn_string)

    try:
        result = add_variations_to_pgn(
            pgn_string,
            args.move,
            num_lines=args.lines,
            depth=args.depth,
            stockfish_path=args.stockfish_path
        )

        print("\n" + "="*60)
        print("MODIFIED PGN WITH VARIATIONS:")
        print("="*60 + "\n")
        print(result)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(result)
            print(f"\nSaved to: {args.output}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
