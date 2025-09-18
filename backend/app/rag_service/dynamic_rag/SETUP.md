# Geo LLM – Dynamic RAG + Frontend: Full Setup & Usage

This guide helps you run the Dynamic RAG backend with the Next.js frontend, upload documents, retrieve similar content, and export embeddings for downstream LLM pipelines.

## Prerequisites
- Windows 10/11 (PowerShell) or macOS/Linux
- Python 3.10+ (3.11 recommended)
- Node.js 18+
- Docker Desktop (for Redis)

## 1) Start Redis (Docker)
- If you already have a Redis container in Docker Desktop, start it and ensure port mapping is `6379:6379`.
- Otherwise:
```powershell
docker run -d --name redis-rag -p 6379:6379 redis:7-alpine
```

If your Redis uses a password, note it for the backend `redis_url` (see below).

## 2) Backend – Dynamic RAG (FastAPI)
```powershell
cd backend/dynamic_rag

# Create .env (defaults shown)
@"
redis_url=redis://localhost:6379/0
use_gpu=false
embedding_model=all-MiniLM-L6-v2
"@ | Out-File -Encoding utf8 .env

# (If Redis has a password)
# redis_url=redis://:YOUR_PASSWORD@localhost:6379/0

# Create and activate venv
python -m venv .venv
. .venv/Scripts/Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify health:
- Root: `http://localhost:8000/`
- Backend health: `http://localhost:8000/health`
- Retrieval health: `http://localhost:8000/api/v1/health`

Notes:
- First embedding model download may take time.
- If Redis isn’t reachable, backend will log a connection error.

## 3) Frontend – Next.js
```powershell
cd frontend

# Point the frontend to the backend API
@" 
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
"@ | Out-File -Encoding utf8 .env.local

npm install
npm run dev
```
Open `http://localhost:3000`.

## 4) Using the App
### Upload
- Use the existing upload icon on the home page.
- Select up to 2 files among `.pdf, .txt, .docx, .md`.
- The backend will extract → chunk → embed → index (per-session).
- You’ll see a banner: `RAG session: <SESSION_ID> · Processed X files · Y chunks`.
- GeoJSON uploads retain the original map workflow.

### Retrieval
- In the home page input, type a query and submit to see backend retrieval results (top chunk content is displayed, full JSON is logged to the browser console).
- API options:
  - Simple (uses the only active session if exactly one exists):
    ```powershell
    irm -Method Post -Uri http://localhost:8000/api/v1/retrieve -ContentType "application/json" -Body (@{query="test query"} | ConvertTo-Json)
    ```
  - Detailed (explicit session, richer metadata):
    ```powershell
    $session = "YOUR_SESSION_ID"
    irm -Method Post -Uri http://localhost:8000/api/v1/retrieve/detailed -ContentType "application/json" -Body (@{session_id=$session; query="test query"; k=5; returnVectors=$false} | ConvertTo-Json)
    ```
  - View the last stored retrieval responses:
    ```
    GET /api/v1/retrieve/last
    GET /api/v1/retrieve/last/{session_id}
    ```

### Embeddings (API)
- List (no vectors):
```
GET /api/v1/session/{session_id}/embeddings?offset=0&limit=20&includeVectors=false
```
- Single chunk (with vector):
```
GET /api/v1/session/{session_id}/embedding/{index_id}?includeVector=true
```
- Export all (NDJSON stream):
```
GET /api/v1/session/{session_id}/export?format=jsonl&includeVectors=true
```
- Save to file (PowerShell):
```powershell
$session = "YOUR_SESSION_ID"
iwr "http://localhost:8000/api/v1/session/$session/export?format=jsonl&includeVectors=true" -OutFile "embeddings_$session.jsonl"
```

## 5) API Summary
- Ingestion
  - `POST /api/v1/upload-temp`: upload up to 2 files; returns `session_id`, counts, quota
- Retrieval
  - `POST /api/v1/retrieve` (simple): `{ query }` → `{ query, retrieved_chunks: [{ content, score }] }`
  - `POST /api/v1/retrieve/detailed`: `{ session_id, query, k, returnVectors? }` → rich response with metadata
  - `GET /api/v1/retrieve/last`: last simple retrieval response (in-memory)
  - `GET /api/v1/retrieve/last/{session_id}`: last detailed retrieval response per session (in-memory)
- Sessions
  - `GET /api/v1/session/{session_id}`
  - `DELETE /api/v1/session/{session_id}`
  - `GET /api/v1/session/{session_id}/stats`
- Embeddings
  - `GET /api/v1/session/{session_id}/embeddings?offset&limit&includeVectors&search&type`
  - `GET /api/v1/session/{session_id}/embedding/{index_id}?includeVector`
  - `GET /api/v1/session/{session_id}/export?format=json|jsonl&includeVectors`

Example detailed retrieval response (abridged):
```json
{
  "session_id": "75196e40-...",
  "query": "What is geospatial analysis?",
  "k": 5,
  "results_count": 2,
  "results": [
    {
      "content": "Geospatial analysis refers to ...",
      "metadata": { "file": "sample.pdf", "page": 3 },
      "similarity_score": 0.8732,
      "index_id": 12
    }
  ],
  "processing_time_ms": 42.7
}
```

Example embedding chunk schema:
```json
{
  "session_id": "...",
  "index_id": 0,
  "content": "...",
  "metadata": { "filename": "...", "type": "text|table|graph", "page_number": 1 },
  "vector_dim": 384,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "embedding_norm": "l2",
  "vector": [optional]
}
```

## 6) Notes & Limits
- Default model: `all-MiniLM-L6-v2` (384-dim)
- Quotas: defaults (2 files/request, 10 files/day/user)
- Session TTL: ~1 hour of inactivity
- Vectors not returned by default in list responses (opt-in via `includeVectors=true`)
 - “Last result” endpoints are in-memory only (cleared on server restart)

## 7) Troubleshooting
- Frontend upload says “Failed to fetch”
  - Ensure `.env.local` has `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1` and the dev server was restarted
  - Backend is running and logs show no errors
  - CORS is open by default in backend (allow_origins=["*"])
- Redis connection errors
  - Confirm container is running and port 6379 is open
  - If password set, use `redis_url=redis://:YOUR_PASSWORD@localhost:6379/0`
- PDF/processing errors
  - Windows: Camelot (tables) may need Ghostscript; OCR needs Tesseract
  - For a quick test, try `.txt` uploads first

## 8) Handoff to LLM pipeline
- Stream all chunks+vectors: `GET /api/v1/session/{id}/export?format=jsonl&includeVectors=true`
- Or paginate with vectors: `GET /api/v1/session/{id}/embeddings?offset&limit&includeVectors=true`
- Keep `session_id` and `index_id` for citations/traceability

---

With Redis running, the backend started, and the frontend pointing to the API, you can upload documents from the homepage, run retrieval, and export embeddings for downstream LLMs.
