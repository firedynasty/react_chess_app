import requests
import chess
import chess.pgn
from io import StringIO

# Your PGN
pgn = """1. d4 d5 2. c4 Nc6 3. cxd5 Qxd5 4. Nc3 Qa5 5. Nf3 e6 6. Bd2 Qb6 7. b3 Bb4 8. e3 Nf6 9. a3 Bd6 10. b4 a5 11. b5 Na7 12. Be2 Nxb5 13. Bxb5+ c6 14. Be2 O-O 15. O-O c5 16. dxc5 Qxc5 17. Na4 Qc6 18. Nd4 Qe8 19. Nb6 Bd7 20. Nxa8 Ba4 21. Qc1 Qxa8 22. Bb5 Rc8 23. Qb2 Bxb5 24. Qxb5 Rc5 25. Qxb7 Qxb7 26. Rfb1 Qd5 27. Rb8+ Bxb8"""

# Parse PGN
game = chess.pgn.read_game(StringIO(pgn))

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
            # No opening data returned - we've gone beyond known opening theory
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
