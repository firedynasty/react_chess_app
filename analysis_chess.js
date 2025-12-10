/**
 * analysis_chess.js
 * Chess analysis utilities - PGN to UCI conversion and game parsing
 * Requires chess.js (chess.min.js) to be loaded first
 */

const AnalysisChess = (function() {
    'use strict';

    /**
     * Convert PGN string to array of UCI moves
     * @param {string} pgn - PGN formatted game string
     * @returns {object} - { moves: string[], error: string|null }
     */
    function pgnToUci(pgn) {
        if (typeof Chess === 'undefined') {
            return { moves: [], error: 'chess.js not loaded' };
        }

        const chess = new Chess();
        const cleanedPgn = cleanPgn(pgn);

        // Try loading as full PGN first
        if (chess.load_pgn(cleanedPgn)) {
            return {
                moves: extractUciMoves(chess),
                error: null
            };
        }

        // If PGN load fails, try parsing as move list
        chess.reset();
        const moveTokens = cleanedPgn.replace(/\d+\./g, '').trim().split(/\s+/);

        for (const token of moveTokens) {
            if (!token || token === '') continue;

            const move = chess.move(token);
            if (!move) {
                return { moves: [], error: `Invalid move: ${token}` };
            }
        }

        return {
            moves: extractUciMoves(chess),
            error: null
        };
    }

    /**
     * Extract UCI moves from a Chess instance
     * @param {Chess} chess - chess.js instance with loaded game
     * @returns {string[]} - Array of UCI format moves
     */
    function extractUciMoves(chess) {
        const history = chess.history({ verbose: true });
        return history.map(move => {
            let uci = move.from + move.to;
            if (move.promotion) {
                uci += move.promotion;
            }
            return uci;
        });
    }

    /**
     * Clean PGN string by removing annotations and comments
     * @param {string} pgn - Raw PGN string
     * @returns {string} - Cleaned PGN
     */
    function cleanPgn(pgn) {
        let cleaned = pgn;

        // Remove NAG annotations ($1, $2, etc.)
        cleaned = cleaned.replace(/\$\d+/g, '');

        // Remove comments in curly braces {comment}
        cleaned = cleaned.replace(/\{[^}]*\}/g, '');

        // Remove variations in parentheses (recursive for nested)
        let prev;
        do {
            prev = cleaned;
            cleaned = cleaned.replace(/\([^()]*\)/g, '');
        } while (cleaned !== prev);

        // Remove clock annotations [%clk ...]
        cleaned = cleaned.replace(/\[%[^\]]*\]/g, '');

        // Remove result strings
        cleaned = cleaned.replace(/1-0|0-1|1\/2-1\/2|\*/g, '');

        // Clean up extra whitespace
        cleaned = cleaned.replace(/\s+/g, ' ').trim();

        return cleaned;
    }

    /**
     * Parse PGN and return game data
     * @param {string} pgn - PGN formatted game string
     * @returns {object} - Game data including moves, headers, positions
     */
    function parseGame(pgn) {
        if (typeof Chess === 'undefined') {
            return { error: 'chess.js not loaded' };
        }

        const chess = new Chess();
        const cleanedPgn = cleanPgn(pgn);

        // Try to load
        let loaded = chess.load_pgn(cleanedPgn);
        if (!loaded) {
            chess.reset();
            const moveTokens = cleanedPgn.replace(/\d+\./g, '').trim().split(/\s+/);
            for (const token of moveTokens) {
                if (!token) continue;
                if (!chess.move(token)) {
                    return { error: `Invalid move: ${token}` };
                }
            }
        }

        const history = chess.history({ verbose: true });
        const positions = [];
        const uciMoves = [];
        const sanMoves = [];

        // Reset to get positions
        chess.reset();
        positions.push(chess.fen());

        for (const move of history) {
            chess.move(move.san);
            positions.push(chess.fen());
            sanMoves.push(move.san);

            let uci = move.from + move.to;
            if (move.promotion) uci += move.promotion;
            uciMoves.push(uci);
        }

        return {
            uciMoves,
            sanMoves,
            positions,
            totalMoves: history.length,
            finalFen: chess.fen(),
            error: null
        };
    }

    /**
     * Convert a single SAN move to UCI format given a FEN position
     * @param {string} fen - Current position in FEN
     * @param {string} san - Move in SAN format (e.g., "Nf3")
     * @returns {object} - { uci: string, error: string|null }
     */
    function sanToUci(fen, san) {
        if (typeof Chess === 'undefined') {
            return { uci: null, error: 'chess.js not loaded' };
        }

        const chess = new Chess(fen);
        const move = chess.move(san);

        if (!move) {
            return { uci: null, error: `Invalid move: ${san}` };
        }

        let uci = move.from + move.to;
        if (move.promotion) uci += move.promotion;

        return { uci, error: null };
    }

    /**
     * Convert UCI move to SAN format given a FEN position
     * @param {string} fen - Current position in FEN
     * @param {string} uci - Move in UCI format (e.g., "e2e4")
     * @returns {object} - { san: string, error: string|null }
     */
    function uciToSan(fen, uci) {
        if (typeof Chess === 'undefined') {
            return { san: null, error: 'chess.js not loaded' };
        }

        const chess = new Chess(fen);

        const from = uci.substring(0, 2);
        const to = uci.substring(2, 4);
        const promotion = uci.length > 4 ? uci[4] : undefined;

        const move = chess.move({ from, to, promotion });

        if (!move) {
            return { san: null, error: `Invalid UCI move: ${uci}` };
        }

        return { san: move.san, error: null };
    }

    /**
     * Validate a FEN string
     * @param {string} fen - FEN string to validate
     * @returns {boolean}
     */
    function isValidFen(fen) {
        if (typeof Chess === 'undefined') return false;

        const chess = new Chess();
        return chess.load(fen);
    }

    /**
     * Get legal moves for a position
     * @param {string} fen - Position in FEN format
     * @returns {object} - { moves: { san: string, uci: string }[], error: string|null }
     */
    function getLegalMoves(fen) {
        if (typeof Chess === 'undefined') {
            return { moves: [], error: 'chess.js not loaded' };
        }

        const chess = new Chess(fen);
        const moves = chess.moves({ verbose: true });

        return {
            moves: moves.map(m => ({
                san: m.san,
                uci: m.from + m.to + (m.promotion || '')
            })),
            error: null
        };
    }

    /**
     * Format move number with notation
     * @param {number} plyIndex - 0-based ply index
     * @returns {string} - Formatted move notation (e.g., "1." or "1...")
     */
    function formatMoveNumber(plyIndex) {
        const moveNum = Math.floor(plyIndex / 2) + 1;
        const isWhite = plyIndex % 2 === 0;
        return isWhite ? `${moveNum}.` : `${moveNum}...`;
    }

    // Public API
    return {
        pgnToUci,
        parseGame,
        cleanPgn,
        sanToUci,
        uciToSan,
        isValidFen,
        getLegalMoves,
        formatMoveNumber
    };
})();

// Export for Node.js/CommonJS
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AnalysisChess;
}
