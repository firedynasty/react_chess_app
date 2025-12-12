================================================================================
FEN BUILDER - LOAD FROM FEN & BUILD PGN TEXTAREA
================================================================================

This document contains all the code needed to implement a Lichess-style
analysis board where you can:
1. Load a FEN position onto a chessboard
2. Make moves (validated by chess.js)
3. Output proper PGN with [Variant "From Position"] header

================================================================================
DEPENDENCIES (CDN)
================================================================================

<!-- jQuery (required by chessboard.js) -->
<script src='https://code.jquery.com/jquery-2.2.4.min.js'></script>

<!-- Chessboard.js - visual board -->
<script src='https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.js'></script>

<!-- Chess.js - move validation & PGN generation -->
<script src='https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js'></script>

<!-- Chessboard.js CSS -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.css">

================================================================================
HTML ELEMENTS
================================================================================

<!-- Input textarea for FEN -->
<textarea id="myTextArea"
    style="width: 100%; height: 60px; margin-top: 10px; padding: 10px;
           border: 2px solid #ccc; border-radius: 5px;
           font-family: monospace; font-size: 14px;"
    placeholder="Paste FEN here... e.g. [FEN &quot;rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1&quot;]">
</textarea><br>

<!-- Chess board container -->
<div id="myBoard" style="width: 400px;"></div><br>

<!-- Current position FEN output -->
<textarea id="myTextArea2"
    style="width: 100%; height: 60px; margin-top: 10px; padding: 10px;
           border: 2px solid #ccc; border-radius: 5px;
           font-family: monospace; font-size: 14px;"
    placeholder="Current position FEN will appear here...">
</textarea><br>

<!-- Move history / PGN output -->
<textarea id="moveHistoryTextArea"
    style="width: 100%; height: 100px; margin-top: 10px; padding: 10px;
           border: 2px solid #4CAF50; border-radius: 5px;
           font-family: monospace; font-size: 14px;"
    placeholder="Move history (PGN) will appear here..."
    readonly>
</textarea><br>

<!-- Buttons -->
<button onclick="loadFenVariantOnBoard()">Load FEN to Board</button>
<button onclick="resetBoard()">Reset Board</button>

================================================================================
JAVASCRIPT - GLOBAL VARIABLES
================================================================================

<script>
    var board = null;           // Chessboard.js instance
    window.chess = null;        // Chess.js instance
    window.startingFen = null;  // Stores the loaded FEN for PGN header
    window.moveHistory = [];    // Array of moves (optional tracking)
</script>

================================================================================
JAVASCRIPT - BOARD INITIALIZATION WITH onDrop
================================================================================

<script>
    function initializeBoard() {
        // Check if dependencies are loaded
        if (typeof Chessboard === 'undefined' || typeof Chess === 'undefined') {
            console.log('Waiting for dependencies...');
            setTimeout(initializeBoard, 100);
            return;
        }

        console.log('Initializing chessboard...');

        // Initialize move history array
        window.moveHistory = [];

        // Initialize chess.js for move validation and PGN generation
        window.chess = new Chess();

        board = Chessboard('myBoard', {
            draggable: true,
            dropOffBoard: 'snapback',
            position: 'start',
            snapbackSpeed: 500,
            snapSpeed: 100,
            pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',

            onDrop: function(source, target, piece, newPos, oldPos, orientation) {
                // Debug logging
                console.log('onDrop:', source, '->', target, 'piece:', piece);
                console.log('chess.js FEN:', window.chess.fen());
                console.log('chess.js turn:', window.chess.turn());

                // Attempt the move using chess.js
                const move = window.chess.move({
                    from: source,
                    to: target,
                    promotion: 'q' // auto-promote to queen
                });

                console.log('Move result:', move);

                if (move === null) {
                    // Invalid move - snap piece back to original position
                    console.log('Invalid move - snapping back');
                    return 'snapback';
                }

                // Valid move - display PGN with custom header format
                // Get just the moves from chess.js pgn (strip any headers)
                let pgnMoves = window.chess.pgn();
                // Remove any existing headers (lines starting with [)
                pgnMoves = pgnMoves.replace(/\[[^\]]*\]\s*/g, '').trim();

                // Build custom PGN with Variant header using the starting FEN
                const startFen = window.startingFen || 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
                const customPgn = '[Variant "From Position"]\n[FEN "' + startFen + '"]\n\n' + pgnMoves;

                console.log('Custom PGN:', customPgn);
                document.getElementById('moveHistoryTextArea').value = customPgn;

                // Update myTextArea2 with the current FEN from chess.js
                const currentFen = window.chess.fen();
                const fenVariant = '[Variant "From Position"][FEN "' + currentFen + '"]';
                document.getElementById('myTextArea2').value = fenVariant;

                // Optional: Copy to clipboard
                navigator.clipboard.writeText(fenVariant).then(function() {
                    console.log('Copied to clipboard:', fenVariant);
                }).catch(function(err) {
                    console.log('Clipboard write failed:', err);
                });
            }
        });

        console.log('Chessboard initialized successfully');
    }

    // Start initialization when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeBoard);
    } else {
        initializeBoard();
    }
</script>

================================================================================
JAVASCRIPT - LOAD FEN VARIANT ON BOARD
================================================================================

<script>
    // Function to load FEN variant from textarea onto the board
    function loadFenVariantOnBoard() {
        const textArea = document.getElementById('myTextArea');
        const content = textArea.value.trim();

        // If empty, show a message
        if (!content) {
            alert('Textarea is empty');
            return;
        }

        try {
            // Extract FEN from variant format like:
            // [Variant "From Position"][FEN "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"]
            const fenMatch = content.match(/\[FEN\s+"([^"]+)"\]/);
            let fenString;

            if (fenMatch && fenMatch[1]) {
                fenString = fenMatch[1];
                console.log('Extracted FEN:', fenString);
            } else {
                // If no FEN variant format found, try to load it as a plain FEN
                fenString = content;
                console.log('Using plain FEN:', fenString);
            }

            // Extract just the position part (before first space) for chessboard.js
            const positionPart = fenString.split(' ')[0];

            // Load position on board
            board.position(positionPart);

            // Sync chess.js with the full FEN (includes turn, castling, move number)
            if (window.chess) {
                const loaded = window.chess.load(fenString);
                if (loaded) {
                    console.log('chess.js synced to FEN:', fenString);
                    // Store the starting FEN for reference
                    window.startingFen = fenString;
                } else {
                    console.log('chess.js failed to load FEN, using position only');
                    // Try with default metadata if FEN is incomplete
                    const fullFen = positionPart + ' w KQkq - 0 1';
                    window.chess.load(fullFen);
                    window.startingFen = fullFen;
                }
            }

            // Clear move history
            window.moveHistory = [];
            document.getElementById('moveHistoryTextArea').value = '';

            // Update myTextArea2 with the loaded FEN variant
            const fenVariant = '[Variant "From Position"][FEN "' + fenString + '"]';
            document.getElementById('myTextArea2').value = fenVariant;

            console.log('FEN loaded! chess.js synced - moves will continue from this position');

        } catch (error) {
            alert('Invalid FEN format: ' + error.message);
            console.error('Error loading FEN variant on board:', error);
        }

        textArea.focus();
    }
</script>

================================================================================
JAVASCRIPT - RESET BOARD
================================================================================

<script>
    // Function to reset the board to starting position
    function resetBoard() {
        // Set up the standard chess starting position
        board.position('start');

        // Clear move history and reset chess.js
        window.moveHistory = [];
        if (window.chess) window.chess.reset();
        window.startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

        document.getElementById('moveHistoryTextArea').value = '';
        document.getElementById('myTextArea').value = '';
        document.getElementById('myTextArea2').value = '';

        console.log('Board reset to starting position');
    }
</script>

================================================================================
COMPLETE MINIMAL WORKING EXAMPLE (SINGLE HTML FILE)
================================================================================

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FEN Builder - Load & Analyze</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 20px auto;
            padding: 20px;
        }
        textarea {
            width: 100%;
            margin: 10px 0;
            padding: 10px;
            font-family: monospace;
            font-size: 14px;
            border: 2px solid #ccc;
            border-radius: 5px;
            box-sizing: border-box;
        }
        #moveHistoryTextArea {
            border-color: #4CAF50;
            height: 120px;
        }
        #myBoard {
            margin: 20px 0;
        }
        button {
            padding: 10px 20px;
            margin: 5px;
            cursor: pointer;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
        }
        button:hover {
            background: #45a049;
        }
        .info {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <h2>FEN Builder - Load & Analyze</h2>

    <div class="info">
        <strong>Instructions:</strong><br>
        1. Paste FEN into the input box below<br>
        2. Click "Load FEN to Board"<br>
        3. Make moves by dragging pieces<br>
        4. PGN output appears in the green box
    </div>

    <label><strong>Input FEN:</strong></label>
    <textarea id="myTextArea" rows="2"
        placeholder='Paste FEN here... e.g. [FEN "r5k1/2N2ppp/p1p5/1p2r1b1/3q4/3P1Q2/PPP2PPP/R3R1K1 w - - 0 17"]'></textarea>

    <div>
        <button onclick="loadFenVariantOnBoard()">Load FEN to Board</button>
        <button onclick="resetBoard()">Reset Board</button>
    </div>

    <div id="myBoard" style="width: 400px;"></div>

    <label><strong>Current Position FEN:</strong></label>
    <textarea id="myTextArea2" rows="2" readonly
        placeholder="Current position FEN updates here after each move..."></textarea>

    <label><strong>PGN Output (with moves):</strong></label>
    <textarea id="moveHistoryTextArea" rows="6" readonly
        placeholder="PGN with move history appears here..."></textarea>

    <!-- Dependencies -->
    <script src='https://code.jquery.com/jquery-2.2.4.min.js'></script>
    <script src='https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.js'></script>
    <script src='https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js'></script>

    <script>
        var board = null;
        window.chess = null;
        window.startingFen = null;
        window.moveHistory = [];

        function initializeBoard() {
            if (typeof Chessboard === 'undefined' || typeof Chess === 'undefined') {
                setTimeout(initializeBoard, 100);
                return;
            }

            window.moveHistory = [];
            window.chess = new Chess();

            board = Chessboard('myBoard', {
                draggable: true,
                dropOffBoard: 'snapback',
                position: 'start',
                snapbackSpeed: 500,
                snapSpeed: 100,
                pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',

                onDrop: function(source, target, piece, newPos, oldPos, orientation) {
                    console.log('onDrop:', source, '->', target, 'piece:', piece);
                    console.log('chess.js FEN:', window.chess.fen());
                    console.log('chess.js turn:', window.chess.turn());

                    const move = window.chess.move({
                        from: source,
                        to: target,
                        promotion: 'q'
                    });

                    console.log('Move result:', move);

                    if (move === null) {
                        console.log('Invalid move - snapping back');
                        return 'snapback';
                    }

                    // Build custom PGN
                    let pgnMoves = window.chess.pgn();
                    pgnMoves = pgnMoves.replace(/\[[^\]]*\]\s*/g, '').trim();

                    const startFen = window.startingFen || 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
                    const customPgn = '[Variant "From Position"]\n[FEN "' + startFen + '"]\n\n' + pgnMoves;

                    console.log('Custom PGN:', customPgn);
                    document.getElementById('moveHistoryTextArea').value = customPgn;

                    const currentFen = window.chess.fen();
                    const fenVariant = '[Variant "From Position"][FEN "' + currentFen + '"]';
                    document.getElementById('myTextArea2').value = fenVariant;

                    navigator.clipboard.writeText(customPgn).catch(function(err) {
                        console.log('Clipboard write failed:', err);
                    });
                }
            });

            console.log('Chessboard initialized');
        }

        function loadFenVariantOnBoard() {
            const textArea = document.getElementById('myTextArea');
            const content = textArea.value.trim();

            if (!content) {
                alert('Textarea is empty');
                return;
            }

            try {
                const fenMatch = content.match(/\[FEN\s+"([^"]+)"\]/);
                let fenString;

                if (fenMatch && fenMatch[1]) {
                    fenString = fenMatch[1];
                } else {
                    fenString = content;
                }

                const positionPart = fenString.split(' ')[0];
                board.position(positionPart);

                if (window.chess) {
                    const loaded = window.chess.load(fenString);
                    if (loaded) {
                        window.startingFen = fenString;
                    } else {
                        const fullFen = positionPart + ' w KQkq - 0 1';
                        window.chess.load(fullFen);
                        window.startingFen = fullFen;
                    }
                }

                window.moveHistory = [];
                document.getElementById('moveHistoryTextArea').value = '';

                const fenVariant = '[Variant "From Position"][FEN "' + fenString + '"]';
                document.getElementById('myTextArea2').value = fenVariant;

                console.log('FEN loaded and chess.js synced');

            } catch (error) {
                alert('Invalid FEN format: ' + error.message);
            }
        }

        function resetBoard() {
            board.position('start');
            window.moveHistory = [];
            if (window.chess) window.chess.reset();
            window.startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
            document.getElementById('moveHistoryTextArea').value = '';
            document.getElementById('myTextArea').value = '';
            document.getElementById('myTextArea2').value = '';
            console.log('Board reset');
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeBoard);
        } else {
            initializeBoard();
        }
    </script>
</body>
</html>

================================================================================
DATA FLOW DIAGRAM
================================================================================

    +------------------+
    |   myTextArea     |  <-- User pastes FEN here
    | (Input FEN)      |
    +--------+---------+
             |
             v
    +--------+---------+
    | loadFenVariant   |  <-- Click "Load FEN to Board"
    | OnBoard()        |
    +--------+---------+
             |
             +--------------------+--------------------+
             |                    |                    |
             v                    v                    v
    +--------+--------+  +--------+--------+  +--------+--------+
    | board.position  |  | chess.load(fen) |  | window.starting |
    | (positionPart)  |  | Syncs chess.js  |  | Fen = fenString |
    | Updates visual  |  | for validation  |  | Stores for PGN  |
    +-----------------+  +-----------------+  +-----------------+

             |
             v  (User drags piece)
    +--------+---------+
    |    onDrop()      |
    | source, target   |
    +--------+---------+
             |
             v
    +--------+---------+
    | chess.move({     |
    |   from: source,  |
    |   to: target     |  --> Returns null if illegal
    | })               |      (piece snaps back)
    +--------+---------+
             |
             v (if valid)
    +--------+---------+
    | chess.pgn()      |  --> Get moves in PGN format
    | Strip headers    |
    | Add custom       |
    | [Variant...] hdr |
    +--------+---------+
             |
             +--------------------+--------------------+
             |                    |                    |
             v                    v                    v
    +--------+--------+  +--------+--------+  +--------+--------+
    | moveHistory     |  | myTextArea2     |  | Clipboard       |
    | TextArea        |  | Current FEN     |  | (optional)      |
    | Shows full PGN  |  | after move      |  |                 |
    +-----------------+  +-----------------+  +-----------------+

================================================================================
EXAMPLE USAGE
================================================================================

INPUT (paste into myTextArea):
[FEN "r5k1/2N2ppp/p1p5/1p2r1b1/3q4/3P1Q2/PPP2PPP/R3R1K1 w - - 0 17"]

CLICK: "Load FEN to Board"

MAKE MOVES:
- Drag white rook e1 to e5 (captures black rook)
- Drag black queen d4 to e5 (captures white rook)
- Drag white pawn d3 to d4
- etc.

OUTPUT (in moveHistoryTextArea):
[Variant "From Position"]
[FEN "r5k1/2N2ppp/p1p5/1p2r1b1/3q4/3P1Q2/PPP2PPP/R3R1K1 w - - 0 17"]

17. Rxe5 Qxe5 18. d4 Rd8 19. Qf4 Qxf4 20. Nd5

================================================================================
KEY CHESS.JS METHODS USED
================================================================================

chess.load(fen)     - Load a position from FEN string
                      Returns: true if valid, false if invalid

chess.move({        - Make a move
  from: 'e2',
  to: 'e4',
  promotion: 'q'    - For pawn promotion (q/r/b/n)
})                    Returns: move object if legal, null if illegal

chess.pgn()         - Get game in PGN format
                      Returns: string with headers and moves

chess.fen()         - Get current position as FEN
                      Returns: FEN string

chess.turn()        - Get whose turn it is
                      Returns: 'w' or 'b'

chess.reset()       - Reset to starting position

chess.undo()        - Undo last move
                      Returns: move object or null

================================================================================
TROUBLESHOOTING
================================================================================

1. "Moves aren't working after loading FEN"
   - Check browser console for errors
   - Verify chess.js FEN matches board position:
     console.log(window.chess.fen())
   - Verify it's the correct turn:
     console.log(window.chess.turn())

2. "PGN shows wrong move numbers"
   - Ensure FEN includes move number (last number in FEN)
   - Example: "...w - - 0 17" means move 17, white to play

3. "Piece snaps back on valid move"
   - chess.js enforces strict rules
   - Check if it's actually that side's turn
   - Check if the move is truly legal

4. "FEN not loading"
   - Verify FEN format is correct
   - Must have all 6 parts: position turn castling en_passant halfmove fullmove
   - Example: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

================================================================================
