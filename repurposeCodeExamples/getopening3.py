import requests
import chess
import chess.pgn
from io import StringIO
import sys

# Get PGN from command line argument or use default
if len(sys.argv) > 1:
    pgn = sys.argv[1]
else:
    print("Usage: python getopening.py '<PGN moves>'")
    print("Example: python getopening.py '1. e4 e5 2. Nf3 Nc6'")
    sys.exit(1)

# Parse PGN
try:
    game = chess.pgn.read_game(StringIO(pgn))
    if game is None:
        print("Error: Invalid PGN format")
        sys.exit(1)
except Exception as e:
    print(f"Error parsing PGN: {e}")
    sys.exit(1)

last_opening_name = None
last_opening_eco = None

# Try different move depths to find opening
for num_moves in range(1, 50):
    test_board = game.board()
    moves = list(game.mainline_moves())[:num_moves]
    
    if not moves or num_moves > len(list(game.mainline_moves())):
        break
    
    for move in moves:
        test_board.push(move)
    
    fen = test_board.fen()
    response = requests.get(f"https://explorer.lichess.ovh/masters?fen={fen}")
    
    try:
        data = response.json()
        if data and 'opening' in data and data['opening']:
            current_name = data['opening']['name']
            current_eco = data['opening']['eco']
            
            # Only print if opening name changed
            if current_name != last_opening_name:
                print(f"After {num_moves} move(s):")
                print(f"  Opening: {current_name}")
                print(f"  ECO: {current_eco}")
                print()
                
                last_opening_name = current_name
                last_opening_eco = current_eco
        else:
            # No opening data returned
            print(f"✓ Opening theory ends after move {num_moves - 1}")
            print(f"  Final Opening: {last_opening_name}")
            print(f"  ECO: {last_opening_eco}")
            break
    except:
        # API error - stop here
        print(f"✓ Opening theory ends after move {num_moves - 1}")
        print(f"  Final Opening: {last_opening_name}")
        print(f"  ECO: {last_opening_eco}")
        break
