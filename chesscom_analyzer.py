#!/usr/bin/env python3
"""
Chess.com Game Analyzer with Pattern Recognition
Fetches games from Chess.com and analyzes them for patterns and mistakes
"""

import requests
import re
from chess_pattern_analyzer import ChessPatternAnalyzer

# Import functions from lichess_check.py if available
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def extract_game_id_from_url(url_or_id):
    """Extract game ID from Chess.com URL or return as-is"""
    if 'chess.com' in url_or_id:
        # Handle URLs like https://www.chess.com/game/live/145318794164
        # or https://www.chess.com/game/daily/12345
        match = re.search(r'/game/(live|daily)/(\d+)', url_or_id)
        if match:
            game_type = match.group(1)
            game_id = match.group(2)
            return game_type, game_id
    return None, url_or_id


class ChesscomGameAnalyzer:
    def __init__(self, stockfish_path=None):
        """
        Initialize Chess.com game analyzer

        Args:
            stockfish_path: Path to Stockfish engine
        """
        self.analyzer = ChessPatternAnalyzer(stockfish_path=stockfish_path)

    def fetch_game_pgn(self, game_url, username=None):
        """
        Fetch PGN from Chess.com for a game URL

        Chess.com doesn't have a direct game-by-ID endpoint, so we:
        1. Ask user for their username
        2. Assume game is from current/latest month
        3. Search monthly archive for the game ID

        Args:
            game_url: Chess.com game URL (e.g., https://www.chess.com/game/live/145318794164)
            username: Chess.com username (will prompt if not provided)

        Returns:
            PGN text string
        """
        # Extract game type and ID from URL
        game_type, game_id = extract_game_id_from_url(game_url)
        
        if not game_type:
            print("Error: Could not parse Chess.com URL")
            print("Expected format: https://www.chess.com/game/live/GAMEID")
            return None

        # Get username if not provided
        if not username:
            username = input("Enter your Chess.com username: ").strip()
            if not username:
                print("Error: Username required")
                return None

        # Chess.com API requires lowercase usernames
        username = username.lower()

        try:
            from datetime import datetime
            
            print(f"Fetching {game_type} game {game_id} from Chess.com...")
            print(f"  → Username: {username}")
            
            # Try current month first
            now = datetime.now()
            year = now.year
            month = str(now.month).zfill(2)
            
            print(f"  → Checking archive for {year}/{month}...")
            
            # Fetch player's monthly archive
            # Add headers to comply with Chess.com API policies
            headers = {
                'User-Agent': 'Chess Pattern Analyzer (Python/requests)'
            }
            archive_url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month}"
            archive_response = requests.get(archive_url, headers=headers, timeout=10)
            archive_response.raise_for_status()
            archive_data = archive_response.json()
            
            # Find our specific game in the archive
            if 'games' not in archive_data:
                print("Error: No games found in archive")
                return None
            
            print(f"  → Searching through {len(archive_data['games'])} games...")
            
            for game in archive_data['games']:
                # Check if this is our game by matching the game ID
                if 'url' in game and game_id in game['url']:
                    if 'pgn' in game:
                        print(f"✓ Game found in archive!")
                        return game['pgn']
            
            # If not found in current month, try previous month
            print(f"  → Game not found in current month, trying previous month...")
            import time
            time.sleep(1)  # Rate limiting - be nice to Chess.com API
            prev_month = now.month - 1
            prev_year = now.year
            if prev_month == 0:
                prev_month = 12
                prev_year -= 1
            
            month = str(prev_month).zfill(2)
            year = prev_year
            
            print(f"  → Checking archive for {year}/{month}...")
            archive_url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month}"
            archive_response = requests.get(archive_url, headers=headers, timeout=10)
            archive_response.raise_for_status()
            archive_data = archive_response.json()
            
            if 'games' in archive_data:
                print(f"  → Searching through {len(archive_data['games'])} games...")
                for game in archive_data['games']:
                    if 'url' in game and game_id in game['url']:
                        if 'pgn' in game:
                            print(f"✓ Game found in archive!")
                            return game['pgn']
            
            print(f"Error: Game {game_id} not found in recent archives")
            print("The game might be:")
            print("  - From a different username (try the other player)")
            print("  - From an older month")
            print("  - Still in progress")
            print("  - Private or deleted")
            return None

        except requests.exceptions.RequestException as e:
            print(f"Error fetching game: {e}")
            print("\nNote: Make sure:")
            print("1. Username is correct (case-sensitive)")
            print("2. The game is completed")
            print("3. The game is public")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_pgn_moves_only(self, pgn_text):
        """
        Extract just the moves from PGN (remove headers and comments)

        Args:
            pgn_text: Full PGN text with headers

        Returns:
            Cleaned PGN with just moves
        """
        lines = pgn_text.split('\n')
        move_lines = []

        for line in lines:
            line = line.strip()
            # Skip empty lines and header lines (starting with [)
            if not line or line.startswith('['):
                continue
            move_lines.append(line)

        # Join all move lines
        moves_text = ' '.join(move_lines)

        # Remove clock annotations
        moves_text = re.sub(r'\{[^}]*\}', '', moves_text)
        # Remove eval annotations
        moves_text = re.sub(r'\([^)]*\)', '', moves_text)
        # Remove Chess.com specific annotations like [%clk 0:05:00]
        moves_text = re.sub(r'\[%[^\]]*\]', '', moves_text)
        # Clean up whitespace
        moves_text = re.sub(r'\s+', ' ', moves_text).strip()

        return moves_text

    def analyze_chesscom_game(self, game_url, username=None, output_file=None):
        """
        Analyze a Chess.com game by URL

        Args:
            game_url: Chess.com game URL
            username: Chess.com username (will prompt if not provided)
            output_file: Optional output filename for report

        Returns:
            Analysis results dict
        """
        # Fetch PGN from Chess.com
        pgn_text = self.fetch_game_pgn(game_url, username)

        if not pgn_text:
            return {'error': 'Could not fetch game from Chess.com'}

        # Extract metadata for report
        game_info = self._extract_game_info(pgn_text)

        print(f"\nGame Info:")
        print(f"  White: {game_info.get('White', 'Unknown')}")
        print(f"  Black: {game_info.get('Black', 'Unknown')}")
        print(f"  Result: {game_info.get('Result', 'Unknown')}")
        print(f"  Date: {game_info.get('Date', 'Unknown')}")
        print()

        # Clean PGN for analysis
        clean_pgn = self.extract_pgn_moves_only(pgn_text)

        # Analyze with pattern analyzer
        results = self.analyzer.analyze_game(clean_pgn)

        if 'error' in results:
            return results

        # Add game metadata
        results['game_info'] = game_info
        results['full_pgn'] = pgn_text  # Store full PGN for report
        game_type, game_id = extract_game_id_from_url(game_url)
        results['game_id'] = game_id
        results['chesscom_url'] = game_url

        # Generate report
        if output_file is None:
            output_file = f"chesscom_analysis_{results['game_id']}.txt"

        self._generate_enhanced_report(results, output_file)

        return results

    def _extract_game_info(self, pgn_text):
        """Extract game metadata from PGN headers"""
        info = {}
        headers = [
            'Event', 'Site', 'Date', 'White', 'Black',
            'Result', 'WhiteElo', 'BlackElo', 'TimeControl',
            'ECO', 'Opening', 'Termination'
        ]

        for header in headers:
            pattern = rf'\[{header} "([^"]+)"\]'
            match = re.search(pattern, pgn_text)
            if match:
                info[header] = match.group(1)

        return info

    def _clean_pgn_for_display(self, pgn_text):
        """
        Clean PGN for display - essential headers + compact moves on one line
        Based on format_moves_compact from lichess_check.py
        """
        # Essential headers to keep
        essential_headers = [
            'Event', 'Site', 'Date', 'Round', 'White', 'Black', 'Result',
            'WhiteElo', 'BlackElo', 'TimeControl', 'ECO', 'Termination'
        ]

        lines = pgn_text.split('\n')
        header_lines = []
        move_lines = []

        # Separate headers and moves
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith('['):
                # Check if essential header
                for header in essential_headers:
                    if line_stripped.startswith(f'[{header} '):
                        header_lines.append(line)
                        break
            elif line_stripped and not line_stripped.startswith('['):
                # This is a move line
                move_lines.append(line_stripped)

        # Format moves compactly with line wrapping
        if move_lines:
            moves_text = ' '.join(move_lines).strip()
            # Remove clock annotations
            moves_text = re.sub(r'\{[^}]*\}', '', moves_text)
            # Remove Chess.com clock: [%clk 0:09:59.7]
            moves_text = re.sub(r'\[%clk[^\]]*\]', '', moves_text)
            # Remove black move numbers (e.g., "1...")
            moves_text = re.sub(r'\d+\.\.\.', '', moves_text)
            # Remove extra whitespace
            moves_text = re.sub(r'\s+', ' ', moves_text).strip()
            # Remove game result at the end if present
            moves_text = re.sub(r'\s+(1-0|0-1|1/2-1/2|\*)\s*$', '', moves_text)

            # Wrap moves to ~70 characters per line
            wrapped_moves = self._wrap_moves(moves_text, max_length=70)

            # Combine: headers + blank line + wrapped moves
            result = '\n'.join(header_lines) + '\n\n' + wrapped_moves + '\n'
            return result

        return '\n'.join(header_lines)

    def _wrap_moves(self, moves_text, max_length=70):
        """
        Wrap PGN moves to specified line length, breaking at move boundaries

        Args:
            moves_text: PGN moves string
            max_length: Maximum characters per line

        Returns:
            Wrapped moves with newlines
        """
        # Split by move numbers to keep move pairs together
        move_pattern = r'(\d+\.\s+\S+(?:\s+\S+)?)'
        moves = re.findall(move_pattern, moves_text)

        lines = []
        current_line = []
        current_length = 0

        for move in moves:
            move_length = len(move)

            # If adding this move would exceed max_length, start new line
            if current_length + move_length + 1 > max_length and current_line:
                lines.append(' '.join(current_line))
                current_line = [move]
                current_length = move_length
            else:
                current_line.append(move)
                current_length += move_length + 1  # +1 for space

        # Add remaining moves
        if current_line:
            lines.append(' '.join(current_line))

        return '\n'.join(lines)

    def _generate_enhanced_report(self, results, output_file):
        """Generate enhanced report with Chess.com-specific features"""
        from datetime import datetime

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("CHESS.COM GAME ANALYSIS REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*70 + "\n\n")

            # Game information
            f.write("GAME INFORMATION\n")
            f.write("-"*70 + "\n")
            game_info = results.get('game_info', {})
            f.write(f"Game URL: {results['chesscom_url']}\n")
            f.write(f"White: {game_info.get('White', 'Unknown')} "
                   f"({game_info.get('WhiteElo', '?')})\n")
            f.write(f"Black: {game_info.get('Black', 'Unknown')} "
                   f"({game_info.get('BlackElo', '?')})\n")
            f.write(f"Result: {game_info.get('Result', 'Unknown')}\n")
            f.write(f"Date: {game_info.get('Date', 'Unknown')}\n")
            f.write(f"Time Control: {game_info.get('TimeControl', 'Unknown')}\n")

            if 'ECO' in game_info:
                f.write(f"Opening (ECO): {game_info.get('ECO', '')}\n")
            if 'Opening' in game_info:
                f.write(f"Opening Name: {game_info.get('Opening', '')}\n")
            if 'Termination' in game_info:
                f.write(f"Termination: {game_info.get('Termination', '')}\n")

            # Add cleaned PGN section
            if 'full_pgn' in results:
                f.write("\n" + "-"*70 + "\n")
                f.write("PGN (Essential Headers + Moves)\n")
                f.write("-"*70 + "\n")

                # Clean PGN - keep only essential headers
                clean_pgn = self._clean_pgn_for_display(results['full_pgn'])
                f.write(clean_pgn)
                f.write("\n")

            f.write("\n")

            # Use the standard report generation from base analyzer
            # Pass file handle to append to the same file instead of overwriting
            self.analyzer.generate_report(results, output_file, file_handle=f)

        # Show full path
        full_path = os.path.abspath(output_file)
        print(f"✓ Enhanced report saved: {full_path}")

    def analyze_multiple_games(self, game_urls, username=None, output_dir='chesscom_reports'):
        """
        Analyze multiple Chess.com games

        Args:
            game_urls: List of game URLs
            username: Chess.com username
            output_dir: Directory to save reports

        Returns:
            List of analysis results
        """
        import os

        os.makedirs(output_dir, exist_ok=True)

        results_list = []

        for i, game_url in enumerate(game_urls, 1):
            print(f"\n{'='*70}")
            print(f"Analyzing game {i}/{len(game_urls)}: {game_url}")
            print(f"{'='*70}")

            game_type, game_id = extract_game_id_from_url(game_url)
            output_file = os.path.join(output_dir, f"analysis_{game_id}.txt")

            result = self.analyze_chesscom_game(game_url, username, output_file)
            results_list.append(result)

            print(f"✓ Completed {i}/{len(game_urls)}")

        # Generate summary report
        self._generate_summary_report(results_list, output_dir)

        return results_list

    def _generate_summary_report(self, results_list, output_dir):
        """Generate summary report for multiple games"""
        from datetime import datetime
        import os

        summary_file = os.path.join(output_dir, 'analysis_summary.txt')

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("MULTI-GAME ANALYSIS SUMMARY (CHESS.COM)\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*70 + "\n\n")

            f.write(f"Total games analyzed: {len(results_list)}\n\n")

            # Aggregate statistics
            total_blunders = sum(r.get('blunders', 0) for r in results_list if 'error' not in r)
            total_mistakes = sum(r.get('mistakes', 0) for r in results_list if 'error' not in r)
            total_inaccuracies = sum(r.get('inaccuracies', 0) for r in results_list if 'error' not in r)
            total_tactical = sum(r.get('tactical_errors', 0) for r in results_list if 'error' not in r)
            total_positional = sum(r.get('positional_errors', 0) for r in results_list if 'error' not in r)

            successful_games = len([r for r in results_list if 'error' not in r])

            f.write("AGGREGATE STATISTICS\n")
            f.write("-"*70 + "\n")
            f.write(f"Successfully analyzed: {successful_games}/{len(results_list)}\n")
            f.write(f"Total blunders: {total_blunders}\n")
            f.write(f"Total mistakes: {total_mistakes}\n")
            f.write(f"Total inaccuracies: {total_inaccuracies}\n")
            f.write(f"Total tactical errors: {total_tactical}\n")
            f.write(f"Total positional errors: {total_positional}\n\n")

            if successful_games > 0:
                # Average per game
                avg_blunders = total_blunders / successful_games
                avg_mistakes = total_mistakes / successful_games

                f.write("AVERAGES PER GAME\n")
                f.write("-"*70 + "\n")
                f.write(f"Average blunders: {avg_blunders:.1f}\n")
                f.write(f"Average mistakes: {avg_mistakes:.1f}\n")
                f.write(f"Average inaccuracies: {total_inaccuracies/successful_games:.1f}\n\n")

            # Individual game summary
            f.write("INDIVIDUAL GAME SUMMARIES\n")
            f.write("-"*70 + "\n\n")

            for result in results_list:
                if 'error' in result:
                    f.write(f"Game: ERROR - {result['error']}\n\n")
                    continue

                game_info = result.get('game_info', {})
                f.write(f"Game: {result['chesscom_url']}\n")
                f.write(f"  {game_info.get('White', '?')} vs {game_info.get('Black', '?')}\n")
                f.write(f"  Blunders: {result.get('blunders', 0)}, ")
                f.write(f"Mistakes: {result.get('mistakes', 0)}, ")
                f.write(f"Inaccuracies: {result.get('inaccuracies', 0)}\n\n")

        # Show full path
        full_path = os.path.abspath(summary_file)
        print(f"\n✓ Summary report saved: {full_path}")


def main():
    """Main function with interactive menu"""
    print("="*70)
    print("CHESS.COM GAME ANALYZER WITH PATTERN RECOGNITION")
    print("="*70)
    print()

    # Create analyzer
    analyzer = ChesscomGameAnalyzer()

    print("Select mode:")
    print("1. Analyze single game by URL")
    print("2. Analyze multiple games")
    print("3. Analyze game from pgnForGenerate.txt")

    choice = input("\nEnter choice (1/2/3): ").strip()

    if choice == "1":
        print("\nEnter your Chess.com username:")
        username = input("Username: ").strip()
        
        if not username:
            print("Error: Username required")
            return
        
        print("\nEnter Chess.com game URL:")
        print("Example: https://www.chess.com/game/live/145318794164")
        game_url = input("URL: ").strip()
        
        if game_url:
            analyzer.analyze_chesscom_game(game_url, username)

    elif choice == "2":
        print("\nEnter your Chess.com username:")
        username = input("Username: ").strip()
        
        if not username:
            print("Error: Username required")
            return
            
        print("\nEnter game URLs (one per line, empty line to finish):")
        print("Example: https://www.chess.com/game/live/145318794164")
        game_urls = []
        while True:
            game_input = input().strip()
            if not game_input:
                break
            game_urls.append(game_input)

        if game_urls:
            analyzer.analyze_multiple_games(game_urls, username=username)

    elif choice == "3":
        # Use the standalone analyzer for local PGN file
        try:
            from chess_pattern_analyzer import main as analyze_local
            analyze_local()
        except ImportError:
            print("Error: chess_pattern_analyzer.py not found")

    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
