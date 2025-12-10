# Added Chess Coach Chat Component to react-chess-analysis_vercel

## Date: 2025-12-10

## Overview
Integrated a React-based chat component into the vanilla JavaScript chess analysis app. The chat allows users to interact with AI (ChatGPT or Claude) for chess coaching feedback.

---

## Files Created

### 1. `/api/chat.js`
Vercel serverless function for proxying OpenAI API calls.

**Features:**
- CORS headers for cross-origin requests
- Supports user's own API key OR shared key with access code
- Proxies requests to OpenAI Chat Completions API
- Environment variables required:
  - `OPENAI_API_KEY` - Your OpenAI API key
  - `ACCESS_CODE` - Password for using Stanley's key

---

## Files Modified

### 1. `/vercel.json`
Updated to support serverless functions alongside static files.

**Before:**
```json
{
  "version": 2,
  "builds": [
    {
      "src": "**/*",
      "use": "@vercel/static"
    }
  ],
  "routes": [...]
}
```

**After:**
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/**/*.js",
      "use": "@vercel/node"
    },
    {
      "src": "**/*",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/api/$1"
    },
    ...
  ]
}
```

### 2. `/index.html`
Added Chess Coach Chat component at the bottom of the page (after line 3199).

**Added:**
- React 18 CDN scripts
- ReactDOM 18 CDN script
- Babel standalone for JSX transformation
- Chat container div (`#chess-chat-root`)
- Inline React component (`<script type="text/babel">`)

---

## Chat Component Features

### UI Layout (Navbar-style)
- **Provider Toggle**: ChatGPT / Claude switch
- **API Key Input**: Password field for user's API key
- **"Use Stanley's Key" Button**: Prompts for access code (ChatGPT only)
- **Model Selection**: Dropdown with available models
- **Load Analysis Report**: Appends `window.analysisReportRawText` to textarea
- **Copy Chat**: Copies conversation to clipboard
- **Clear Chat**: Clears all messages

### Chess Coaching Prompt Buttons
1. **Move Analysis** - "You are a direct chess coach. Analyze move [X] in my game..."
2. **Full Game Review** - "Act as a chess instructor providing comprehensive game analysis..."
3. **Position Analysis** - "Be a direct chess coach. In this position [FEN], I played [move]..."

### Chat Area
- Max height: 400px (scrollable)
- Auto-scrolls to newest messages
- User messages: Cyan background (#00d4ff)
- Assistant messages: Dark background (#1a1a2e)
- Loading indicator while waiting for response

### Input Area
- Resizable textarea (60px - 200px height)
- Enter to send, Shift+Enter for new line
- Send button disabled when empty or loading

---

## Available Models

### ChatGPT (OpenAI)
- GPT-4o
- GPT-4o Mini (default)
- GPT-4 Turbo
- GPT-3.5 Turbo
- o1
- o1 Mini

### Claude (Anthropic)
- Claude 3.5 Haiku (default)
- Claude 3.5 Sonnet
- Claude Sonnet 4
- Claude Opus 4.5

---

## How It Works

1. **Load Analysis Report**: Clicks button → reads `window.analysisReportRawText` → appends to textarea
2. **Prompt Buttons**: Clicks button → appends coaching prompt to textarea
3. **Send Message**:
   - ChatGPT + Own Key + Localhost → Direct OpenAI API call
   - ChatGPT + Production/Shared Key → `/api/chat` serverless function
   - Claude → Direct Anthropic API call (with browser access header)

---

## Styling
- Matches existing dark theme
- Colors: `#1a1a2e` (dark), `#0f3460` (panel), `#00d4ff` (accent)
- Panel style consistent with rest of app

---

## Deployment Notes

### Required Environment Variables (Vercel Dashboard)
```
OPENAI_API_KEY=sk-...
ACCESS_CODE=your_password
```

### Deploy Command
```bash
cd react-chess-analysis_vercel
vercel --prod
```

---

## Known Issues / Notes

1. **Babel Warning**: "You are using the in-browser Babel transformer" - This is expected when using inline JSX. For production optimization, JSX could be precompiled, but it works as-is.

2. **404 on /api/chat**: If you get this error, ensure:
   - `api/chat.js` file exists
   - `vercel.json` has the `@vercel/node` build config
   - Project has been redeployed to Vercel

3. **Claude API**: Requires `anthropic-dangerous-direct-browser-access: true` header for browser calls.
