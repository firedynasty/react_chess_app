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
// Same routing as `lf`: try the Mac Studio first (bigger model, ~3 s connect
// timeout), fall back to this laptop's Ollama.
//   OLLAMA_URL    force one host (skips the Studio/laptop choice)
//   STUDIO_URL    default http://Stanleys-Mac-Studio.local:11434
//   STUDIO_MODEL  default inkling-2-mini
//   OLLAMA_MODEL  force a model; otherwise Studio -> STUDIO_MODEL,
//                 laptop -> the largest installed model with "qwen" in its name
//   OLLAMA_CTX    context window, default 32768 (knowledge base alone is ~10k tokens)
const STUDIO_URL = (process.env.STUDIO_URL || 'http://Stanleys-Mac-Studio.local:11434').replace(/\/$/, '');
const STUDIO_MODEL = process.env.STUDIO_MODEL || 'inkling-2-mini';
const LAPTOP_URL = 'http://localhost:11434';
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

async function tags(url, timeoutMs) {
    const r = await fetch(url + '/api/tags', { signal: AbortSignal.timeout(timeoutMs) });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return (await r.json()).models || [];
}

// Picked once, then reused; cleared after a failed call so the next request
// re-checks (Studio asleep -> laptop, Studio back -> Studio).
let backend = null;   // { url, model }
async function ollamaBackend() {
    if (backend) return backend;
    const pick = (url, models, preferred) => {
        if (process.env.OLLAMA_MODEL) return process.env.OLLAMA_MODEL;
        if (preferred && models.some(m => m.name === preferred || m.name === preferred + ':latest')) return preferred;
        const qwen = models.filter(m => /qwen/i.test(m.name)).sort((a, b) => b.size - a.size);
        if (qwen.length) return qwen[0].name;
        throw new Error('No usable model at ' + url + ' — set OLLAMA_MODEL');
    };
    if (process.env.OLLAMA_URL) {
        const url = process.env.OLLAMA_URL.replace(/\/$/, '');
        backend = { url, model: pick(url, await tags(url, 10000)) };
    } else {
        try {
            backend = { url: STUDIO_URL, model: pick(STUDIO_URL, await tags(STUDIO_URL, 3000), STUDIO_MODEL) };
        } catch (e) {
            console.log('Mac Studio not reachable (' + (e.message || e) + '), using this laptop');
            backend = { url: LAPTOP_URL, model: pick(LAPTOP_URL, await tags(LAPTOP_URL, 5000)) };
        }
    }
    console.log('Local AI:', backend.model, 'at', backend.url);
    return backend;
}

async function ollamaChat(messages) {
    const { url, model } = await ollamaBackend();
    let r;
    try {
        r = await fetch(url + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model,
            messages,
            stream: false,
            think: false,
            options: { num_ctx: OLLAMA_CTX },
        }),
        });
    } catch (e) { backend = null; throw e; }
    const text = await r.text();
    if (!r.ok) { backend = null; throw new Error('Ollama (' + model + '): ' + text); }
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
