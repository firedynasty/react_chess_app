const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8000;

const mimeTypes = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
};

// ── Local AI: /api/chat and /api/rag-chess answered by Ollama ──────────────
// Only under `npm start`. On Vercel the api/ functions still go to OpenAI.
// The page still asks for an access code / key; anything works here, it's ignored.
//   OLLAMA_URL   default http://localhost:11434
//   OLLAMA_MODEL default: the largest installed model with "qwen" in its name
//   OLLAMA_CTX   context window, default 32768 (knowledge base alone is ~10k tokens)
const OLLAMA_URL = (process.env.OLLAMA_URL || 'http://localhost:11434').replace(/\/$/, '');
const OLLAMA_CTX = parseInt(process.env.OLLAMA_CTX || '32768', 10);

let CHESS_KNOWLEDGE = '';
try { CHESS_KNOWLEDGE = fs.readFileSync(path.join(__dirname, 'chess_knowledge.txt'), 'utf8'); } catch (e) { }

// Same system prompt as api/rag-chess.py
const CHESS_SYSTEM_PROMPT = `You are a chess coach with deep knowledge of chess principles and strategies.

When analyzing games or positions:
1. Reference specific chess principles when applicable - cite them explicitly
2. If analyzing a full game, cover the opening, middlegame, and endgame phases
3. If analyzing a specific move, compare it with alternatives/variations when provided
4. Explain strategic and tactical implications clearly
5. When variations are provided, explain why one line is better than another
6. Provide actionable improvement suggestions
7. Use a Socratic approach - ask thought-provoking questions to help the player discover insights
8. Recommend specific practice resources (lichess puzzles, opening explorers) when relevant

CHESS KNOWLEDGE BASE:
${CHESS_KNOWLEDGE}`;

let resolvedModel = process.env.OLLAMA_MODEL || null;
async function ollamaModel() {
    if (resolvedModel) return resolvedModel;
    const r = await fetch(OLLAMA_URL + '/api/tags');
    const { models = [] } = await r.json();
    const qwen = models.filter(m => /qwen/i.test(m.name)).sort((a, b) => b.size - a.size);
    if (!qwen.length) throw new Error('No qwen model in Ollama — set OLLAMA_MODEL');
    resolvedModel = qwen[0].name;
    console.log('Local AI model:', resolvedModel);
    return resolvedModel;
}

async function ollamaChat(messages) {
    const r = await fetch(OLLAMA_URL + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: await ollamaModel(),
            messages,
            stream: false,
            options: { num_ctx: OLLAMA_CTX },
        }),
    });
    const text = await r.text();
    if (!r.ok) throw new Error('Ollama: ' + text);
    const content = (JSON.parse(text).message?.content || '');
    return content.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
}

function readJson(req) {
    return new Promise((resolve, reject) => {
        let buf = '';
        req.on('data', c => { buf += c; });
        req.on('end', () => { try { resolve(buf ? JSON.parse(buf) : {}); } catch (e) { reject(e); } });
        req.on('error', reject);
    });
}

async function handleLocalAi(req, res, route) {
    const send = (code, obj) => {
        res.writeHead(code, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(obj));
    };
    try {
        const body = await readJson(req);
        let messages = Array.isArray(body.messages) ? body.messages.slice() : [];
        if (route === '/api/rag-chess') {
            if (body.query) messages.push({ role: 'user', content: body.query });
            messages = [{ role: 'system', content: CHESS_SYSTEM_PROMPT }, ...messages];
        }
        const t0 = Date.now();
        const content = await ollamaChat(messages);
        console.log(`${route} answered in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
        send(200, route === '/api/rag-chess' ? { content, query: body.query || '' } : { content });
    } catch (e) {
        console.error(route, e);
        send(500, { error: e.message || String(e) });
    }
}

const server = http.createServer((req, res) => {
    const route = req.url.split('?')[0];
    if (req.method === 'POST' && (route === '/api/chat' || route === '/api/rag-chess')) {
        handleLocalAi(req, res, route);
        return;
    }
    const urlPath = decodeURIComponent(req.url.split('?')[0].split('#')[0]);
    let filePath = urlPath === '/' ? '/index.html' : urlPath;
    filePath = path.join(__dirname, filePath);

    const ext = path.extname(filePath);
    const contentType = mimeTypes[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, content) => {
        if (err) {
            if (err.code === 'ENOENT') {
                res.writeHead(404);
                res.end('File not found');
            } else {
                res.writeHead(500);
                res.end('Server error');
            }
        } else {
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(content);
        }
    });
});

server.listen(PORT, () => {
    console.log(`Chess Analyzer running at http://localhost:${PORT}`);
});
