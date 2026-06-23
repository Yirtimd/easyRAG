# easyRAG

**A personal document intelligence system with a Chrome extension.**  
Index any PDF or webpage text, then chat with your knowledge base — from anywhere in your browser.

---

## Overview

easyRAG is a self-hosted RAG (Retrieval-Augmented Generation) service paired with a Chrome extension. Each user gets an isolated document index and a persistent chat history. The backend runs as a single Docker container and can be deployed to any cloud platform in minutes.

```
Browser Extension  ──►  FastAPI Backend  ──►  LLM (any OpenAI-compatible API)
      │                       │
      │                  ChromaDB (per-user)
      │                  SQLite / Postgres (chat history)
      │
   Right-click any page  ──►  "Add to RAG"
   Paste text in popup   ──►  Indexed instantly
   Upload PDF            ──►  Chunked and stored
   Ask a question        ──►  Streaming answer
```

---

## Features

- **Per-user isolation** — every API key maps to a private ChromaDB collection
- **PDF ingestion** — upload directly from the extension popup
- **Text ingestion** — paste any text or use the browser context menu on selected text
- **Streaming chat** — answers appear word by word, conversation history persists across sessions
- **Export** — download your entire knowledge base as a JSON file
- **Docker-ready** — single `docker build` and `docker run`
- **Any LLM** — works with OpenAI, DeepSeek, Gemini, or any OpenAI-compatible endpoint

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.12 |
| Vector store | ChromaDB (persistent, per-user collections) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Chat history | SQLAlchemy + SQLite (or Postgres) |
| LLM client | OpenAI SDK (any compatible endpoint) |
| Extension | Chrome Manifest V3, vanilla JS |
| Deployment | Docker |

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/your-username/easyRAG.git
cd easyRAG
cp .env.example .env
```

Edit `.env`:

```env
OPENROUTER_API_KEY=your_key
BASE_URL=https://api.apiyi.com/v1        # or any OpenAI-compatible endpoint
BASE_MODEL=deepseek-v3                   # or gpt-4o-mini, gemini-2.5-flash, etc.
DATABASE_URL=sqlite:///./qa.db
```

### 2. Run with Docker

```bash
docker build -t easyrag .
docker run -p 8000:8000 --env-file .env easyrag
```

### 3. Create your API key

```bash
curl -X POST http://localhost:8000/auth/register
# → { "id": 1, "api_key": "sk-abc123..." }
```

### 4. Ingest a document

```bash
curl -X POST http://localhost:8000/ingest \
  -H "x-api-key: sk-abc123..." \
  -F "file=@your_document.pdf"
```

### 5. Chat

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk-abc123..." \
  -d '{"question": "Summarize the key points", "session_id": "my-session"}'
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | — | Create a new user, returns `api_key` |
| `GET` | `/health` | — | Service health check |
| `POST` | `/ingest` | ✓ | Upload and index a PDF file |
| `POST` | `/ingest/text` | ✓ | Index plain text with a source label |
| `POST` | `/chat` | ✓ | Streaming chat against your documents |
| `GET` | `/history/{session_id}` | ✓ | Retrieve conversation history |
| `GET` | `/export` | ✓ | Export full knowledge base as JSON |

All authenticated endpoints require the header `x-api-key: sk-...`

---

## Chrome Extension

The extension lives in the `chrome_extension/` folder.

### Install (developer mode)

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `chrome_extension/` folder

### Usage

| Action | How |
|---|---|
| Add selected text | Right-click any selected text → **Add to easyRAG** |
| Paste text manually | Open extension → **Add** tab → paste and submit |
| Upload PDF | Open extension → **Add** tab → choose file → **Index PDF** |
| Chat | Open extension → **Chat** tab |
| Get API key | Open extension → **Key** tab → **Get new key** |
| Export knowledge base | Click the download icon in the header |

> After installing, go to the **Key** tab, click **Get new key**, and make sure your server URL is set correctly in `popup.js` (`SERVER_URL` constant).

---

## Project Structure

```
easyRAG/
├── main.py          # FastAPI app, endpoints, streaming
├── agent.py         # Agent loop with tool calling
├── tools.py         # RAG search, history tools, tool dispatcher
├── ingest.py        # PDF parser, text chunker, ChromaDB writer
├── database.py      # SQLAlchemy models, user auth, chat history
├── requirements.txt
├── Dockerfile
├── .env.example
└── chrome_extension/
    ├── manifest.json
    ├── popup.html
    ├── popup.js
    ├── background.js
    ├── content.js
    └── icons/
```

---

## Deployment

### Railway / Timeweb / Render

1. Push this repo to GitHub
2. Connect to your cloud provider
3. Set environment variables (same as `.env`)
4. Add a managed Postgres database and set `DATABASE_URL`
5. Deploy — the `Dockerfile` handles everything

> **Note:** ChromaDB uses local disk storage. After each redeploy, re-index your documents via `/ingest`. For production use, consider replacing ChromaDB with a persistent vector store like Pinecone or Qdrant.

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `OPENROUTER_API_KEY` | API key for your LLM provider | `sk-...` |
| `BASE_URL` | OpenAI-compatible base URL | `https://api.apiyi.com/v1` |
| `BASE_MODEL` | Model name | `deepseek-v3` |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./qa.db` |

---

## License

MIT
