#!/usr/bin/env node

const path = require("path");
const loadEngine = require("./examples/loadEngine.js");

// Your game moves in UCI format
const moves = [
    "e2e4", "d7d5", "e4d5", "d8d5", "b1c3", "d5a5", "f1c4", "g8f6",
    "a2a4", "b8c6", "g1f3", "e7e5", "d2d3", "f8c5", "e1g1", "c6d4",
    "f1e1", "e8g8", "e1e5", "c8g4", "c3e4", "f6e4", "d3e4", "d4f3",
    "g2f3", "g4h3", "e5d5", "c7c6", "d5d3", "a5c7", "c1g5", "h7h6",
    "g5h4", "g8h8", "h4g3", "c7e7", "d3d7", "e7g5", "d7f7", "f8f7",
    "c4f7", "h6h5", "f3f4", "g5e7", "f7g6", "e7e6", "d1h5", "h8g8",
    "g6f7", "e6f7", "h5h3", "a8d8", "h3f1", "d8d2", "a1d1", "d2c2",
    "d1d8", "g8h7", "f1h3", "h7g6", "h3g4", "g6h7", "g4h4", "h7g6",
    "d8h8", "f7d7", "f4f5", "g6f7", "h4h5", "f7e7", "g3h4", "e7d6",
    "h5g6", "d6c7", "h8g8", "c2c1", "g1g2", "c1c2", "g8g7", "c2b2"
];

const DEPTH = 12;  // Analysis depth
const BLUNDER_THRESHOLD = 150;   // centipawns (1.5 pawns)
const MISTAKE_THRESHOLD = 75;    // centipawns (0.75 pawns)
const INACCURACY_THRESHOLD = 35; // centipawns (0.35 pawns)

let engine;
let results = [];

function parseScore(info) {
    // Parse score from info string
    const mateMatch = info.match(/score mate (-?\d+)/);
    if (mateMatch) {
        const mateIn = parseInt(mateMatch[1]);
        // Convert mate to centipawns (large value)
        return mateIn > 0 ? 10000 - mateIn * 10 : -10000 - mateIn * 10;
    }

    const cpMatch = info.match(/score cp (-?\d+)/);
    if (cpMatch) {
        return parseInt(cpMatch[1]);
    }
    return null;
}

function analyzePosition(moveIndex) {
    return new Promise((resolve) => {
        const movesUpToNow = moves.slice(0, moveIndex);
        const posCmd = movesUpToNow.length > 0
            ? `position startpos moves ${movesUpToNow.join(" ")}`
            : "position startpos";

        let lastScore = null;
        let bestMove = null;

        engine.send(posCmd);
        engine.send(`go depth ${DEPTH}`, (data) => {
            // Parse bestmove
            const match = data.match(/bestmove\s+(\S+)/);
            if (match) {
                bestMove = match[1];
            }
            resolve({ score: lastScore, bestMove });
        }, (line) => {
            // Stream handler - get the deepest score
            if (line.includes("score")) {
                const score = parseScore(line);
                if (score !== null) {
                    lastScore = score;
                }
            }
        });
    });
}

async function analyzeGame() {
    console.log("Loading Stockfish.js engine...\n");

    engine = loadEngine(path.join(__dirname, "src", "stockfish.js"));

    // Wait for engine to be ready
    await new Promise((resolve) => {
        engine.send("uci", () => {
            engine.send("isready", resolve);
        });
    });

    console.log("Engine ready. Analyzing game...\n");
    console.log("=".repeat(70));

    let prevScore = null;
    let prevBestMove = null;

    for (let i = 0; i <= moves.length; i++) {
        const isWhiteToMove = i % 2 === 0;
        const moveNumber = Math.floor(i / 2) + 1;

        const { score, bestMove } = await analyzePosition(i);

        // Flip score to always be from White's perspective
        const whiteScore = isWhiteToMove ? score : -score;

        if (i > 0 && prevScore !== null && score !== null) {
            const playedMove = moves[i - 1];
            const wasWhiteMove = (i - 1) % 2 === 0;
            const moveNum = Math.floor((i - 1) / 2) + 1;

            // Calculate evaluation change from the perspective of the side that moved
            const prevWhiteScore = wasWhiteMove ? prevScore : -prevScore;
            const currWhiteScore = isWhiteToMove ? score : -score;

            // If White moved, a decrease in score is bad. If Black moved, an increase (for White) is bad.
            let evalChange;
            if (wasWhiteMove) {
                evalChange = currWhiteScore - prevWhiteScore;  // Negative = White got worse
            } else {
                evalChange = prevWhiteScore - currWhiteScore;  // Negative = Black got worse (White improved)
            }

            let classification = "";
            let emoji = "";

            if (evalChange <= -BLUNDER_THRESHOLD) {
                classification = "BLUNDER";
                emoji = "??";
            } else if (evalChange <= -MISTAKE_THRESHOLD) {
                classification = "MISTAKE";
                emoji = "?";
            } else if (evalChange <= -INACCURACY_THRESHOLD) {
                classification = "INACCURACY";
                emoji = "?!";
            }

            if (classification) {
                const side = wasWhiteMove ? "White" : "Black";
                const displayMoveNum = wasWhiteMove ? `${moveNum}.` : `${moveNum}...`;
                console.log(`${displayMoveNum} ${playedMove} ${emoji} (${classification})`);
                console.log(`   ${side} played: ${playedMove}`);
                console.log(`   Best was: ${prevBestMove || "?"}`);
                console.log(`   Eval change: ${evalChange > 0 ? "+" : ""}${(evalChange / 100).toFixed(2)}`);
                console.log(`   Position eval: ${whiteScore > 0 ? "+" : ""}${(whiteScore / 100).toFixed(2)}`);
                console.log("");
            }

            results.push({
                moveNumber: moveNum,
                move: playedMove,
                side: wasWhiteMove ? "White" : "Black",
                evalBefore: prevWhiteScore,
                evalAfter: currWhiteScore,
                evalChange,
                classification,
                bestMove: prevBestMove
            });
        }

        prevScore = score;
        prevBestMove = bestMove;

        // Progress indicator
        if (i % 10 === 0) {
            process.stdout.write(`Analyzing move ${i}/${moves.length}...\r`);
        }
    }

    console.log("\n" + "=".repeat(70));
    console.log("\nSUMMARY:");

    const blunders = results.filter(r => r.classification === "BLUNDER");
    const mistakes = results.filter(r => r.classification === "MISTAKE");
    const inaccuracies = results.filter(r => r.classification === "INACCURACY");

    const whiteBlunders = blunders.filter(r => r.side === "White").length;
    const blackBlunders = blunders.filter(r => r.side === "Black").length;
    const whiteMistakes = mistakes.filter(r => r.side === "White").length;
    const blackMistakes = mistakes.filter(r => r.side === "Black").length;
    const whiteInaccuracies = inaccuracies.filter(r => r.side === "White").length;
    const blackInaccuracies = inaccuracies.filter(r => r.side === "Black").length;

    console.log("\n           White    Black");
    console.log(`Blunders:    ${whiteBlunders}        ${blackBlunders}`);
    console.log(`Mistakes:    ${whiteMistakes}        ${blackMistakes}`);
    console.log(`Inaccuracies:${whiteInaccuracies}        ${blackInaccuracies}`);

    engine.quit();
}

analyzeGame().catch(console.error);

