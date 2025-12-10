#!/usr/bin/env python3
"""
Chess Coach CLI - Socratic Coaching from the Terminal
======================================================
A command-line tool that analyzes chess games using:
- Stockfish engine for position evaluation (local, accurate)
- Lichess API for opening theory (book moves)
- Claude for AI-powered Socratic coaching

Usage:
    python chess_coach_cli.py "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6..."
    python chess_coach_cli.py  # Interactive mode (prompts for PGN)

Requirements:
    - Stockfish installed (brew install stockfish)
    - ANTHROPIC_API_KEY for coaching (or enter interactively)

Cost-Saving Tip:
    If using Claude Code, you can skip the API key entirely!
    Claude Code can:
    1. Run the Lichess API analysis (free - no API key needed)
    2. Provide the Socratic coaching directly in the conversation

    Just give Claude Code a PGN and ask it to:
    - Find opening deviations and mistakes using Stockfish + Lichess
    - Act as your Socratic chess coach right there in the terminal
"""

import argparse
import os
import sys
import re
import io
import time
import subprocess
from datetime import datetime
import chess
import chess.pgn
import chess.engine
import requests
import anthropic
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

# ============================================================================
# CONSTANTS
# ============================================================================

BLUNDER_THRESHOLD = -200
MISTAKE_THRESHOLD = -100
INACCURACY_THRESHOLD = -50

# Stockfish paths to try
STOCKFISH_PATHS = [
    '/usr/local/bin/stockfish',
    '/usr/bin/stockfish',
    '/opt/homebrew/bin/stockfish',
    'stockfish',
    './stockfish'
]

AVAILABLE_MODELS = {
    "1": ("Claude 3.5 Haiku", "claude-3-5-haiku-20241022"),
    "2": ("Claude 3.5 Sonnet", "claude-3-5-sonnet-20241022"),
    "3": ("Claude Sonnet 4", "claude-sonnet-4-20250514"),
}

# Terminal colors
class Colors:
    RED = '\033[91m'
    ORANGE = '\033[93m'
    YELLOW = '\033[33m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class OpeningDeviation:
    move_number: int
    notation: str
    move_played: str
    main_line_move: str
    main_line_percentage: float
    alternatives: str
    total_games: int
    fen: str
    opening_name: str = ""
    is_white: bool = True


@dataclass
class MoveError:
    move_number: int
    notation: str
    move: str
    severity: str
    eval_before: float
    eval_after: float
    swing: float
    fen: str
    is_white: bool = True
    tags: List[str] = None  # Tags for puzzle recommendations (e.g., 'fork', 'hanging')

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


# ============================================================================
# LICHESS API FUNCTIONS
# ============================================================================

def get_opening_info(fen: str) -> Optional[Dict]:
    """Get opening name from Lichess Explorer API"""
    try:
        response = requests.get(
            f"https://explorer.lichess.ovh/masters?fen={requests.utils.quote(fen)}",
            timeout=5
        )
        if response.ok:
            data = response.json()
            if data.get('opening'):
                return {
                    'eco': data['opening'].get('eco', ''),
                    'name': data['opening'].get('name', '')
                }
    except Exception:
        pass
    return None


def get_opening_moves(fen: str) -> Optional[Dict]:
    """Get book moves and statistics from Lichess Explorer"""
    try:
        response = requests.get(
            f"https://explorer.lichess.ovh/masters?fen={requests.utils.quote(fen)}&topGames=0",
            timeout=5
        )
        if response.ok:
            data = response.json()
            if data.get('moves') and len(data['moves']) > 0:
                total_games = data.get('white', 0) + data.get('draws', 0) + data.get('black', 0)
                moves = []
                for m in data['moves'][:5]:
                    m_total = m.get('white', 0) + m.get('draws', 0) + m.get('black', 0)
                    pct = (m_total / total_games * 100) if total_games > 0 else 0
                    moves.append({
                        'san': m['san'],
                        'games': m_total,
                        'percentage': round(pct, 1)
                    })
                return {
                    'moves': moves,
                    'total_games': total_games,
                    'opening': data.get('opening')
                }
    except Exception:
        pass
    return None


def get_daily_puzzle() -> Optional[Dict]:
    """Get the daily puzzle from Lichess"""
    try:
        response = requests.get("https://lichess.org/api/puzzle/daily", timeout=5)
        if response.ok:
            data = response.json()
            puzzle_info = data.get('puzzle', {})
            return {
                'rating': puzzle_info.get('rating', 'N/A'),
                'themes': puzzle_info.get('themes', []),
                'url': 'https://lichess.org/training/daily'
            }
    except Exception:
        pass
    return None


def get_theme_description(theme: str) -> str:
    """Get human-readable description for puzzle themes"""
    descriptions = {
        'hangingPiece': 'Win material by capturing undefended pieces',
        'fork': 'Attack two or more pieces simultaneously',
        'backRankMate': 'Deliver checkmate on the back rank',
        'pin': 'Attack a piece that cannot move without exposing a more valuable piece',
        'skewer': 'Attack a valuable piece, forcing it to move and exposing another',
        'discoveredAttack': 'Move a piece to reveal an attack from another piece',
        'exposedKing': 'Exploit a king with weak defenses',
        'middlegame': 'Tactical puzzles from the middlegame',
        'endgame': 'Tactical puzzles from the endgame',
        'sacrifice': 'Win by sacrificing material for a better position',
    }
    return descriptions.get(theme, 'Practice this tactical pattern')


def get_lichess_puzzles(tags: List[str]) -> List[Dict]:
    """Get puzzle recommendations based on detected mistake patterns"""
    theme_mapping = {
        'hanging': 'hangingPiece',
        'fork': 'fork',
        'pin': 'pin',
        'skewer': 'skewer',
        'backrank': 'backRankMate',
        'positional': 'endgame',
        'tactical': 'middlegame',
        'exposed_king': 'exposedKing',
    }

    lichess_themes = []
    for tag in tags:
        if tag in theme_mapping:
            lichess_themes.append(theme_mapping[tag])

    if not lichess_themes:
        lichess_themes = ['middlegame']

    puzzles = []
    seen_themes = set()
    for theme in lichess_themes:
        if theme not in seen_themes:
            seen_themes.add(theme)
            puzzles.append({
                'theme': theme,
                'url': f'https://lichess.org/training/{theme}',
                'description': get_theme_description(theme)
            })

    # Add daily puzzle as bonus
    daily = get_daily_puzzle()
    if daily:
        themes_str = ', '.join(daily['themes'][:3]) if daily['themes'] else 'various'
        puzzles.append({
            'theme': 'Daily Puzzle',
            'url': daily['url'],
            'description': f"Today's puzzle (Rating: {daily['rating']}, Themes: {themes_str})",
            'is_daily': True
        })

    return puzzles


# ============================================================================
# STOCKFISH ENGINE
# ============================================================================

def find_stockfish() -> Optional[str]:
    """Find Stockfish on the system"""
    for path in STOCKFISH_PATHS:
        if os.path.isfile(path):
            return path
    # Try which command
    try:
        result = subprocess.run(['which', 'stockfish'],
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    return None


class StockfishEvaluator:
    """Wrapper for Stockfish engine evaluation"""

    def __init__(self, depth: int = 18, time_limit: float = 0.5):
        self.depth = depth
        self.time_limit = time_limit
        self.engine = None
        self.stockfish_path = find_stockfish()

    def start(self):
        """Start the engine"""
        if not self.stockfish_path:
            raise FileNotFoundError(
                "Stockfish not found. Install with: brew install stockfish"
            )
        self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        return self

    def stop(self):
        """Stop the engine"""
        if self.engine:
            self.engine.quit()
            self.engine = None

    def evaluate(self, board: chess.Board) -> Dict:
        """Evaluate a position, returns score in centipawns from White's perspective"""
        if not self.engine:
            self.start()

        try:
            info = self.engine.analyse(
                board,
                chess.engine.Limit(depth=self.depth, time=self.time_limit)
            )
            score = info['score'].white().score(mate_score=10000)
            best_move = info.get('pv', [None])[0]

            return {
                'score': score,
                'depth': self.depth,
                'best_move': board.san(best_move) if best_move else None
            }
        except Exception as e:
            print(f"{Colors.RED}Engine error: {e}{Colors.RESET}")
            return {'score': 0, 'best_move': None}

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.stop()

    def analyze_move(self, board: chess.Board, move_san: str) -> Dict:
        """Analyze a specific move and return eval before/after"""
        if not self.engine:
            self.start()

        try:
            # Eval before
            eval_before = self.evaluate(board)

            # Make the move
            board_copy = board.copy()
            move = board_copy.parse_san(move_san)
            board_copy.push(move)

            # Eval after
            eval_after = self.evaluate(board_copy)

            return {
                'move': move_san,
                'eval_before': eval_before['score'],
                'eval_after': eval_after['score'],
                'best_move': eval_before.get('best_move')
            }
        except Exception as e:
            return {'error': str(e)}

    def compare_moves(self, fen: str, moves: List[str]) -> List[Dict]:
        """Compare multiple candidate moves from a position"""
        if not self.engine:
            self.start()

        board = chess.Board(fen)
        results = []

        for move_san in moves:
            try:
                board_copy = board.copy()
                move = board_copy.parse_san(move_san)
                board_copy.push(move)
                eval_result = self.evaluate(board_copy)

                results.append({
                    'move': move_san,
                    'score': eval_result['score'],
                    'score_display': eval_result['score'] / 100
                })
            except Exception as e:
                results.append({'move': move_san, 'error': str(e)})

        # Sort by score (best for side to move)
        is_white = board.turn == chess.WHITE
        results.sort(key=lambda x: x.get('score', -99999), reverse=is_white)

        return results


def analyze_position_with_stockfish(fen: str, candidate_moves: List[str] = None) -> Dict:
    """Quick utility to analyze a position and compare moves"""
    with StockfishEvaluator(depth=18, time_limit=0.5) as engine:
        board = chess.Board(fen)

        # Get best move
        eval_result = engine.evaluate(board)

        result = {
            'fen': fen,
            'eval': eval_result['score'] / 100,
            'best_move': eval_result.get('best_move')
        }

        # Compare candidate moves if provided
        if candidate_moves:
            result['candidates'] = engine.compare_moves(fen, candidate_moves)

        return result


# ============================================================================
# CHESS ANALYSIS
# ============================================================================

def detect_error_tags(board: chess.Board, move: chess.Move, swing: int) -> List[str]:
    """
    Detect basic tactical patterns to recommend appropriate puzzles.
    Returns a list of tags like 'hanging', 'fork', 'backrank', etc.
    """
    tags = []

    # Check for hanging pieces (undefended pieces that can be captured)
    our_color = board.turn  # Color that just moved (board is after the move)
    opponent_color = not our_color

    # Check if we left a piece hanging
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.color == opponent_color:
            # Check if this piece is attacked and under-defended
            attackers = board.attackers(our_color, square)
            defenders = board.attackers(opponent_color, square)
            if attackers and len(attackers) > len(defenders):
                if piece.piece_type != chess.PAWN:  # Ignore pawns
                    tags.append('hanging')
                    break

    # Check for potential fork (opponent attacks multiple pieces)
    for opp_move in board.legal_moves:
        to_square = opp_move.to_square
        board.push(opp_move)
        attacked = board.attacks(to_square)
        valuable_attacked = 0
        for sq in attacked:
            p = board.piece_at(sq)
            if p and p.color == opponent_color and p.piece_type in [chess.QUEEN, chess.ROOK, chess.KING]:
                valuable_attacked += 1
        board.pop()
        if valuable_attacked >= 2:
            tags.append('fork')
            break

    # Check for backrank weakness
    king_square = board.king(opponent_color)
    if king_square:
        king_rank = chess.square_rank(king_square)
        if (opponent_color == chess.WHITE and king_rank == 0) or \
           (opponent_color == chess.BLACK and king_rank == 7):
            # Check if king is potentially trapped on back rank
            tags.append('backrank')

    # Large swings often indicate tactical blunders
    if swing <= -300:
        if 'tactical' not in tags:
            tags.append('tactical')

    return tags


def clean_pgn(pgn: str) -> str:
    """Remove annotations from PGN"""
    cleaned = re.sub(r'\$\d+', '', pgn)
    cleaned = re.sub(r'\{[^}]*\}', '', cleaned)
    cleaned = re.sub(r'\([^)]*\)', '', cleaned)
    cleaned = re.sub(r'\[%[^\]]*\]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def analyze_game(pgn_text: str) -> Tuple[List[OpeningDeviation], List[MoveError], Optional[Dict]]:
    """Analyze a chess game and return deviations and errors."""
    pgn_text = clean_pgn(pgn_text)

    board = chess.Board()
    moves = []

    # Try to parse as PGN first
    try:
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        if game:
            moves = list(game.mainline_moves())
    except Exception:
        pass

    # If PGN parsing failed, try as move list
    if not moves:
        board.reset()
        move_text = re.sub(r'\d+\.+', '', pgn_text)
        move_tokens = move_text.strip().split()
        for token in move_tokens:
            token = token.strip()
            if not token or token in ['1-0', '0-1', '1/2-1/2', '*']:
                continue
            try:
                move = board.parse_san(token)
                moves.append(move)
                board.push(move)
            except Exception:
                continue

    if not moves:
        return [], [], None

    total_moves = len(moves)
    board.reset()

    # Phase 1: Detect opening deviations
    print(f"\n{Colors.CYAN}Phase 1: Checking opening theory...{Colors.RESET}")
    opening_deviations = []
    opening_info = None
    left_book = False

    temp_board = chess.Board()
    for i, move in enumerate(moves[:30]):
        if left_book:
            break

        fen_before = temp_board.fen()
        move_san = temp_board.san(move)
        move_num = i // 2 + 1
        is_white = i % 2 == 0
        notation = f"{move_num}." if is_white else f"{move_num}..."

        book_data = get_opening_moves(fen_before)
        temp_board.push(move)

        opening = get_opening_info(temp_board.fen())
        if opening:
            opening_info = opening

        if book_data and book_data['moves']:
            book_moves = [m['san'] for m in book_data['moves']]
            is_book_move = move_san in book_moves

            if not is_book_move:
                left_book = True
                top_move = book_data['moves'][0]
                alternatives = ', '.join([f"{m['san']} ({m['percentage']}%)" for m in book_data['moves'][:3]])

                opening_deviations.append(OpeningDeviation(
                    move_number=move_num,
                    notation=notation,
                    move_played=move_san,
                    main_line_move=top_move['san'],
                    main_line_percentage=top_move['percentage'],
                    alternatives=alternatives,
                    total_games=book_data['total_games'],
                    fen=fen_before,
                    opening_name=opening_info['name'] if opening_info else "",
                    is_white=is_white
                ))
                print(f"  Found deviation at {notation} {move_san}")
        elif not book_data or not book_data['moves']:
            left_book = True

    # Phase 2: Evaluate all positions with Stockfish
    print(f"\n{Colors.CYAN}Phase 2: Evaluating positions with Stockfish...{Colors.RESET}")
    board.reset()
    evaluations = []

    with StockfishEvaluator(depth=15, time_limit=0.3) as engine:
        print(f"  {Colors.GREEN}✓ Stockfish started{Colors.RESET}")

        eval_result = engine.evaluate(board)
        evaluations.append(eval_result['score'] if eval_result else 0)

        for i, move in enumerate(moves):
            board.push(move)
            eval_result = engine.evaluate(board)
            evaluations.append(eval_result['score'] if eval_result else evaluations[-1])

            # Progress indicator
            progress = (i + 1) / total_moves
            bar_width = 30
            filled = int(bar_width * progress)
            bar = '█' * filled + '░' * (bar_width - filled)
            print(f"\r  [{bar}] {i+1}/{total_moves}", end='', flush=True)

    print()  # New line after progress bar

    # Phase 3: Find mistakes
    print(f"\n{Colors.CYAN}Phase 3: Identifying mistakes...{Colors.RESET}")
    board.reset()
    move_errors = []

    for i, move in enumerate(moves):
        move_san = board.san(move)
        move_num = i // 2 + 1
        is_white = i % 2 == 0
        notation = f"{move_num}." if is_white else f"{move_num}..."
        fen_before = board.fen()

        eval_before = evaluations[i]
        eval_after = evaluations[i + 1]

        if is_white:
            swing = eval_after - eval_before
            eval_before_display = eval_before
            eval_after_display = eval_after
        else:
            swing = eval_before - eval_after
            eval_before_display = -eval_before
            eval_after_display = -eval_after

        board.push(move)

        severity = None
        if swing <= BLUNDER_THRESHOLD:
            severity = 'BLUNDER'
        elif swing <= MISTAKE_THRESHOLD:
            severity = 'MISTAKE'
        elif swing <= INACCURACY_THRESHOLD:
            severity = 'INACCURACY'

        if severity:
            # Detect basic pattern tags for puzzle recommendations
            tags = detect_error_tags(board, move, swing)

            move_errors.append(MoveError(
                move_number=move_num,
                notation=notation,
                move=move_san,
                severity=severity,
                eval_before=eval_before_display,
                eval_after=eval_after_display,
                swing=swing,
                fen=fen_before,
                is_white=is_white,
                tags=tags
            ))
            color = Colors.RED if severity == 'BLUNDER' else Colors.ORANGE if severity == 'MISTAKE' else Colors.YELLOW
            print(f"  {color}{severity}{Colors.RESET}: {notation} {move_san}")

    return opening_deviations, move_errors, opening_info


# ============================================================================
# COACHING PROMPTS
# ============================================================================

def build_coaching_system_prompt(context_type: str, context_data: dict) -> str:
    """Build the system prompt for Claude coaching"""

    base_prompt = """You are a thoughtful chess coach using the Socratic method. Your role is to guide players to discover insights rather than lecturing them.

COACHING PRINCIPLES:
1. Start with validation - find what's reasonable in their thinking
2. Ask probing questions - help them discover what they missed
3. Teach principles - connect to broader chess understanding
4. Give concrete actions - one specific thing to study or practice

TONE: Encouraging, curious, thought-provoking. Like a wise mentor, not a critic.

IMPORTANT:
- Don't just cite engine evaluations
- Help build intuition and pattern recognition
- Keep responses focused and under 200 words
- End with a thought-provoking question or concrete study suggestion
"""

    if context_type == "deviation":
        dev = context_data
        return base_prompt + f"""

CURRENT CONTEXT - OPENING DEVIATION:
- Move played: {dev['move_played']}
- Main theory: {dev['main_line']} ({dev['percentage']}% of master games)
- Alternatives: {dev['alternatives']}
- Opening: {dev['opening_name']}
- Position (FEN): {dev['fen']}

Focus on helping them understand opening principles and why theory developed this way."""

    elif context_type == "error":
        err = context_data
        return base_prompt + f"""

CURRENT CONTEXT - {err['severity']}:
- Move played: {err['notation']} {err['move']}
- Evaluation change: {err['eval_before']:.2f} → {err['eval_after']:.2f}
- Position (FEN): {err['fen']}

Focus on helping them understand what they missed and how to spot similar patterns."""

    return base_prompt


def get_prompt_starters(item, item_type: str) -> List[str]:
    """Get sentence starters for the user"""
    if item_type == "deviation":
        opening = item.opening_name if item.opening_name else "this opening"
        return [
            f"I played {item.move_played} instead of {item.main_line_move} because ",
            f"I considered {item.main_line_move} but I thought ",
            f"After {item.move_played}, my plan was to ",
            f"I avoided {item.main_line_move} because I was worried about ",
        ]
    else:
        return [
            f"I played {item.notation} {item.move} because ",
            f"With {item.move}, I was trying to ",
            f"After playing {item.move}, I realize I didn't see ",
            f"I expected my opponent to respond with ",
        ]


# ============================================================================
# CLI INTERFACE
# ============================================================================

def print_header():
    """Print the app header"""
    print(f"""
{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║           ♟️  CHESS COACH CLI - Socratic Coaching             ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
""")


def print_divider():
    print(f"{Colors.DIM}{'─' * 64}{Colors.RESET}")


def save_report(deviations: List[OpeningDeviation], errors: List[MoveError],
                opening: Optional[Dict], pgn_text: str) -> str:
    """Save analysis report to a file with today's date"""
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"chess_report_{today}.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("CHESS GAME ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        # Game PGN
        f.write("GAME PGN\n")
        f.write("-" * 70 + "\n")
        f.write(pgn_text + "\n\n")

        # Opening info
        if opening:
            f.write(f"Opening: {opening.get('eco', '')} {opening.get('name', '')}\n\n")

        # Summary
        blunders = sum(1 for e in errors if e.severity == 'BLUNDER')
        mistakes = sum(1 for e in errors if e.severity == 'MISTAKE')
        inaccuracies = sum(1 for e in errors if e.severity == 'INACCURACY')

        f.write("SUMMARY\n")
        f.write("-" * 70 + "\n")
        f.write(f"Blunders: {blunders}\n")
        f.write(f"Mistakes: {mistakes}\n")
        f.write(f"Inaccuracies: {inaccuracies}\n")
        f.write(f"Opening deviations: {len(deviations)}\n\n")

        # Opening deviations
        if deviations:
            f.write("OPENING DEVIATIONS\n")
            f.write("-" * 70 + "\n")
            for dev in deviations:
                f.write(f"{dev.notation} {dev.move_played} (book: {dev.main_line_move} {dev.main_line_percentage}%)\n")
                f.write(f"  Alternatives: {dev.alternatives}\n")
                fen_encoded = dev.fen.replace(' ', '_')
                f.write(f"  https://lichess.org/analysis/{fen_encoded}\n\n")

        # Mistakes & Blunders
        if errors:
            f.write("MISTAKES & BLUNDERS\n")
            f.write("-" * 70 + "\n")
            for err in errors:
                eval_str = f"{err.eval_before/100:+.2f} → {err.eval_after/100:+.2f}"
                f.write(f"{err.severity}: {err.notation} {err.move}\n")
                f.write(f"  Eval: {eval_str} ({err.swing/100:+.2f})\n\n")

        # Recommended puzzles
        all_tags = []
        for err in errors:
            all_tags.extend(err.tags)
        if len(errors) > 2:
            all_tags.append('tactical')

        f.write("=" * 70 + "\n")
        f.write("RECOMMENDED PUZZLES TO PRACTICE\n")
        f.write("=" * 70 + "\n\n")

        if all_tags:
            puzzles = get_lichess_puzzles(all_tags)
            f.write("Based on your game, practice these puzzle themes on Lichess:\n\n")
            for puzzle in puzzles:
                theme_name = puzzle['theme'].replace('_', ' ').title()
                f.write(f"🎯 {theme_name}\n")
                f.write(f"   {puzzle['description']}\n")
                f.write(f"   Practice: {puzzle['url']}\n")
                if puzzle.get('is_daily'):
                    f.write(f"   ⭐ Bonus: Today's featured puzzle!\n")
                f.write("\n")
        else:
            f.write("Great job! No significant weaknesses detected.\n")
            f.write("Keep practicing at: https://lichess.org/training\n\n")

        # Key positions
        key_positions = [err for err in errors if err.severity in ['BLUNDER', 'MISTAKE']]
        if key_positions:
            f.write("=" * 70 + "\n")
            f.write("KEY POSITIONS TO REVIEW\n")
            f.write("=" * 70 + "\n\n")
            f.write("Review these critical positions:\n\n")

            for err in key_positions[:5]:
                f.write(f"Move {err.notation} {err.move}\n")
                fen_encoded = err.fen.replace(' ', '_')
                f.write(f"  https://lichess.org/analysis/{fen_encoded}\n\n")

    return filename


def display_analysis_results(deviations: List[OpeningDeviation],
                             errors: List[MoveError],
                             opening: Optional[Dict]):
    """Display analysis results in a formatted way"""
    print(f"\n{Colors.BOLD}═══ ANALYSIS RESULTS ═══{Colors.RESET}\n")

    if opening:
        print(f"{Colors.GREEN}Opening: {opening.get('eco', '')} {opening.get('name', '')}{Colors.RESET}\n")

    # Summary stats
    blunders = sum(1 for e in errors if e.severity == 'BLUNDER')
    mistakes = sum(1 for e in errors if e.severity == 'MISTAKE')
    inaccuracies = sum(1 for e in errors if e.severity == 'INACCURACY')

    print(f"📊 Summary:")
    print(f"   {Colors.RED}Blunders: {blunders}{Colors.RESET}")
    print(f"   {Colors.ORANGE}Mistakes: {mistakes}{Colors.RESET}")
    print(f"   {Colors.YELLOW}Inaccuracies: {inaccuracies}{Colors.RESET}")
    if deviations:
        print(f"   {Colors.BLUE}Opening deviations: {len(deviations)}{Colors.RESET}")
    print()

    # List all items for selection
    items = []

    if deviations:
        print(f"{Colors.BOLD}📚 OPENING DEVIATIONS:{Colors.RESET}")
        for i, dev in enumerate(deviations):
            idx = len(items) + 1
            items.append(('deviation', dev))
            print(f"  [{idx}] {dev.notation} {dev.move_played} (book: {dev.main_line_move} {dev.main_line_percentage}%)")
            print(f"      {Colors.DIM}Alternatives: {dev.alternatives}{Colors.RESET}")
        print()

    if errors:
        print(f"{Colors.BOLD}⚠️  MISTAKES & BLUNDERS:{Colors.RESET}")
        for i, err in enumerate(errors):
            idx = len(items) + 1
            items.append(('error', err))
            color = Colors.RED if err.severity == 'BLUNDER' else Colors.ORANGE if err.severity == 'MISTAKE' else Colors.YELLOW
            eval_str = f"{err.eval_before/100:+.2f} → {err.eval_after/100:+.2f}"
            print(f"  [{idx}] {color}{err.severity}{Colors.RESET}: {err.notation} {err.move}")
            print(f"      {Colors.DIM}Eval: {eval_str} ({err.swing/100:+.2f}){Colors.RESET}")
        print()

    if not items:
        print(f"{Colors.GREEN}Great game! No significant mistakes found.{Colors.RESET}")
        return items

    # Collect tags for puzzle recommendations
    all_tags = []
    for err in errors:
        all_tags.extend(err.tags)

    # Add general categories based on error counts
    if len(errors) > 2:
        all_tags.append('tactical')

    # RECOMMENDED PUZZLES SECTION
    print(f"\n{Colors.BOLD}{'═' * 64}{Colors.RESET}")
    print(f"{Colors.BOLD}RECOMMENDED PUZZLES TO PRACTICE{Colors.RESET}")
    print(f"{Colors.BOLD}{'═' * 64}{Colors.RESET}\n")

    if all_tags:
        puzzles = get_lichess_puzzles(all_tags)
        print(f"Based on your game, practice these puzzle themes on Lichess:\n")
        for puzzle in puzzles:
            theme_name = puzzle['theme'].replace('_', ' ').title()
            print(f"🎯 {Colors.CYAN}{theme_name}{Colors.RESET}")
            print(f"   {puzzle['description']}")
            print(f"   Practice: {Colors.BLUE}{puzzle['url']}{Colors.RESET}")
            if puzzle.get('is_daily'):
                print(f"   {Colors.YELLOW}⭐ Bonus: Today's featured puzzle!{Colors.RESET}")
            print()
    else:
        print(f"Great job! No significant weaknesses detected.")
        print(f"Keep practicing at: https://lichess.org/training\n")

    # KEY POSITIONS SECTION (only blunders and mistakes)
    key_positions = [err for err in errors if err.severity in ['BLUNDER', 'MISTAKE']]
    if key_positions:
        print(f"{Colors.BOLD}{'═' * 64}{Colors.RESET}")
        print(f"{Colors.BOLD}KEY POSITIONS TO REVIEW{Colors.RESET}")
        print(f"{Colors.BOLD}{'═' * 64}{Colors.RESET}\n")
        print(f"Review these critical positions:\n")

        for err in key_positions[:5]:  # Top 5 key positions
            color = Colors.RED if err.severity == 'BLUNDER' else Colors.ORANGE
            print(f"{color}Move {err.notation}{Colors.RESET} {err.move}")
            fen_encoded = err.fen.replace(' ', '_')
            print(f"  {Colors.BLUE}https://lichess.org/analysis/{fen_encoded}{Colors.RESET}")
            print()

    return items


def chat_about_item(client: anthropic.Anthropic, model: str, item, item_type: str):
    """Start a chat session about a specific item"""
    print_divider()

    if item_type == "deviation":
        opening_label = f" in {item.opening_name}" if item.opening_name else ""
        print(f"\n{Colors.BOLD}Discussing:{Colors.RESET} {item.notation} {item.move_played}{opening_label}")
        print(f"{Colors.DIM}(deviation from {item.main_line_move}){Colors.RESET}")

        context = {
            "type": "deviation",
            "move_played": item.move_played,
            "main_line": item.main_line_move,
            "percentage": item.main_line_percentage,
            "alternatives": item.alternatives,
            "opening_name": item.opening_name,
            "fen": item.fen
        }
    else:
        print(f"\n{Colors.BOLD}Discussing:{Colors.RESET} {item.notation} {item.move} ({item.severity})")
        print(f"{Colors.DIM}Eval: {item.eval_before/100:+.2f} → {item.eval_after/100:+.2f}{Colors.RESET}")

        context = {
            "type": "error",
            "severity": item.severity,
            "notation": item.notation,
            "move": item.move,
            "eval_before": item.eval_before / 100,
            "eval_after": item.eval_after / 100,
            "fen": item.fen
        }

    # Show Lichess link
    fen_encoded = item.fen.replace(' ', '_')
    print(f"{Colors.CYAN}Analyze on Lichess: https://lichess.org/analysis/{fen_encoded}{Colors.RESET}\n")

    # Show prompt starters
    starters = get_prompt_starters(item, item_type)
    print(f"{Colors.BOLD}Complete your thought (or type your own):{Colors.RESET}")
    for i, starter in enumerate(starters, 1):
        print(f"  [{i}] {starter}...")
    print()

    # Build system prompt
    system_prompt = build_coaching_system_prompt(context["type"], context)
    messages = []

    # Chat loop
    while True:
        user_input = input(f"{Colors.BOLD}You:{Colors.RESET} ").strip()

        if not user_input:
            continue

        if user_input.lower() in ['quit', 'exit', 'q', 'back', 'b']:
            print(f"\n{Colors.DIM}Returning to analysis...{Colors.RESET}\n")
            break

        # Check if user selected a starter
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(starters):
                # Let them complete the starter
                completion = input(f"{Colors.DIM}{starters[idx]}{Colors.RESET}").strip()
                user_input = starters[idx] + completion

        messages.append({"role": "user", "content": user_input})

        print(f"\n{Colors.CYAN}Coach is thinking...{Colors.RESET}")

        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages
            )

            assistant_msg = response.content[0].text
            messages.append({"role": "assistant", "content": assistant_msg})

            print(f"\n{Colors.GREEN}{Colors.BOLD}Coach:{Colors.RESET} {assistant_msg}\n")

        except Exception as e:
            print(f"\n{Colors.RED}Error: {str(e)}{Colors.RESET}\n")
            messages.pop()  # Remove failed message


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Chess Coach CLI - Analyze games with Socratic coaching"
    )
    parser.add_argument(
        "pgn",
        nargs="?",
        default=None,
        help="PGN or move list to analyze (e.g., '1. e4 e5 2. Nf3 Nc6...')"
    )
    parser.add_argument(
        "--model",
        choices=["1", "2", "3", "haiku", "sonnet", "sonnet4"],
        default="1",
        help="Claude model: 1/haiku, 2/sonnet, 3/sonnet4 (default: 1)"
    )
    args = parser.parse_args()

    print_header()

    # Get API key (optional - coaching requires it, analysis doesn't)
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        api_key = input(f"{Colors.BOLD}Enter your Anthropic API key (press Enter to skip coaching):{Colors.RESET} ").strip()

    # Initialize client if API key provided
    client = None
    model_id = None
    if api_key:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            # Select model
            model_map = {"haiku": "1", "sonnet": "2", "sonnet4": "3"}
            model_choice = model_map.get(args.model, args.model)

            if args.pgn:
                model_name, model_id = AVAILABLE_MODELS[model_choice]
                print(f"{Colors.DIM}Using {model_name}{Colors.RESET}")
            else:
                print(f"\n{Colors.BOLD}Select Claude model:{Colors.RESET}")
                for key, (name, _) in AVAILABLE_MODELS.items():
                    print(f"  [{key}] {name}")

                model_choice = input(f"\nChoice (default=1): ").strip() or "1"
                if model_choice not in AVAILABLE_MODELS:
                    model_choice = "1"

                model_name, model_id = AVAILABLE_MODELS[model_choice]
                print(f"{Colors.DIM}Using {model_name}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.YELLOW}Warning: Could not initialize Claude client: {e}{Colors.RESET}")
            print(f"{Colors.DIM}Continuing with analysis only (no coaching){Colors.RESET}")
            client = None
    else:
        print(f"{Colors.DIM}Running analysis only (no coaching){Colors.RESET}")

    print_divider()

    # If PGN provided via argument, use it directly
    pgn_text = args.pgn

    # Main loop
    while True:
        if not pgn_text:
            print(f"\n{Colors.BOLD}Enter your PGN or moves:{Colors.RESET}")
            print(f"{Colors.DIM}(Paste moves, then press Enter twice, or type 'quit' to exit){Colors.RESET}\n")

            # Collect multi-line input
            lines = []
            while True:
                try:
                    line = input()
                    if line.lower() in ['quit', 'exit', 'q']:
                        print(f"\n{Colors.CYAN}Thanks for using Chess Coach CLI!{Colors.RESET}")
                        sys.exit(0)
                    if line == '' and lines:
                        break
                    lines.append(line)
                except EOFError:
                    break

            pgn_text = '\n'.join(lines).strip()

        if not pgn_text:
            print(f"{Colors.YELLOW}No moves entered. Please try again.{Colors.RESET}")
            continue

        # Analyze the game
        print(f"\n{Colors.BOLD}Analyzing game...{Colors.RESET}")
        deviations, errors, opening = analyze_game(pgn_text)

        if not deviations and not errors:
            print(f"\n{Colors.GREEN}Great game! No significant issues found.{Colors.RESET}")
            print(f"{Colors.DIM}(Enter a new game or type 'quit' to exit){Colors.RESET}")
            pgn_text = None  # Reset to prompt for new input
            continue

        # Display results
        items = display_analysis_results(deviations, errors, opening)

        # Save report to file
        report_file = save_report(deviations, errors, opening, pgn_text)
        print(f"\n{Colors.GREEN}✓ Report saved to: {report_file}{Colors.RESET}")

        if not items:
            pgn_text = None
            continue

        # Only show coaching options if client is available
        if not client:
            print(f"\n{Colors.DIM}(No API key provided - coaching disabled){Colors.RESET}")
            print(f"{Colors.DIM}Enter 'n' for new game or 'q' to quit{Colors.RESET}")

        # Item selection loop
        while True:
            print_divider()
            if client:
                print(f"\n{Colors.BOLD}Select a move to discuss (1-{len(items)}), or:{Colors.RESET}")
            else:
                print(f"\n{Colors.BOLD}Options:{Colors.RESET}")
            print(f"  [n] Enter new game")
            print(f"  [q] Quit")

            choice = input(f"\nChoice: ").strip().lower()

            if choice in ['q', 'quit', 'exit']:
                print(f"\n{Colors.CYAN}Thanks for using Chess Coach CLI!{Colors.RESET}")
                sys.exit(0)

            if choice in ['n', 'new']:
                pgn_text = None  # Reset to prompt for new input
                break

            # Only allow coaching if client is available
            if not client:
                print(f"{Colors.YELLOW}Coaching requires an API key. Enter 'n' for new game or 'q' to quit.{Colors.RESET}")
                continue

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    item_type, item = items[idx]
                    chat_about_item(client, model_id, item, item_type)
                else:
                    print(f"{Colors.YELLOW}Invalid choice. Please select 1-{len(items)}.{Colors.RESET}")
            except ValueError:
                print(f"{Colors.YELLOW}Invalid choice. Please enter a number or command.{Colors.RESET}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.CYAN}Goodbye!{Colors.RESET}")
        sys.exit(0)
