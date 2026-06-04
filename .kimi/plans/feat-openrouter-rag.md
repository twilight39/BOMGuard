# Plan: OpenRouter RAG (`feat/openrouter-rag`)

## Goal
Build a working RAG (Retrieval-Augmented Generation) pipeline using OpenRouter for LLM inference, with pgvector for similarity search on regulatory summaries.

## Current State

### Backend
- `backend/bomguard/services/llm_service.py` — `RegulatoryLLMService` exists but:
  - Configured for Google Gemini (`gemini-2.5-flash`, `text-embedding-004`)
  - `ask()` returns `{"answer": "Not implemented yet.", "sources": []}`
  - No embedding generation logic
  - No pgvector search logic
- `backend/bomguard/api/ask.py` — REST and WebSocket endpoints exist but return hardcoded "Not implemented yet"
- `backend/bomguard/models/database.py` — `RegulatorySummary` model exists with `pgvector` embedding column (`embedding: Mapped[Vector(768)]`)
- `backend/bomguard/models/database.py` — `Substance` model exists with name, CAS, SMILES
- No OpenRouter client exists
- No regulatory summary generation logic exists

### Frontend
- `frontend/src/pages/AskPage.tsx` — static heading only, no chat input, no API calls
- No streaming response handling
- No message history

### Available Keys
- `OPENROUTER_API_KEY` in `.env`
- `GEMINI_API_KEY` still available as fallback

## Architecture Decisions (Already Made)
- PostgreSQL + pgvector for embeddings (768-dim Gemini embeddings)
- FastAPI with native WebSocket support
- React 19 + TypeScript frontend
- Chart.js over Recharts (DECISIONS.md)
- Docker Compose deployment

## Implementation Steps

### 1. Create OpenRouter Client

Create `backend/bomguard/services/openrouter_client.py`:
```python
class OpenRouterClient:
    BASE_URL = "https://openrouter.ai/api/v1"
    
    async def chat(self, messages: list[dict], model: str = "anthropic/claude-3.5-sonnet", stream: bool = False) -> str | AsyncIterator[str]:
        ...
```
- Use `httpx.AsyncClient` with streaming support
- Handle rate limits (429) with backoff
- Support model selection (Claude 3.5 Sonnet as default, GPT-4o, Llama 3.1, etc.)
- Include `HTTP-Referer` and `X-Title` headers for OpenRouter ranking

### 2. Embedding Strategy Decision

**Critical decision needed:** OpenRouter does not provide embeddings directly. Options:

**Option A: Keep Gemini for embeddings, use OpenRouter for chat**
- Pros: Existing pgvector schema is 768-dim (Gemini). No migration needed.
- Cons: Two AI providers. More API keys to manage.

**Option B: Switch to OpenAI-compatible embeddings via OpenRouter**
- OpenRouter supports some embedding models, but selection is limited.
- Would require schema migration if dimensions change.

**Option C: Use local sentence-transformers for embeddings**
- `all-MiniLM-L6-v2` (384-dim) or `all-mpnet-base-v2` (768-dim)
- Free, no API calls, but requires CPU/GPU
- Would need schema migration

**Recommended: Option A** — keep Gemini embeddings (already configured), add OpenRouter for chat. Document this dual-provider setup in DECISIONS.md. This minimizes schema changes.

### 3. Generate Regulatory Summaries

Create `backend/bomguard/services/summary_generator.py`:
- For each `Substance` in the database, generate a regulatory summary using the LLM
- Prompt template includes: substance name, CAS, restricted regulations, molecular properties
- Save summary text + Gemini embedding to `regulatory_summaries` table
- Idempotent: skip if summary already exists and is recent

Celery task: `generate_regulatory_summaries(batch_size=50)`

### 4. RAG Pipeline

Refactor `backend/bomguard/services/llm_service.py`:
```python
class RegulatoryLLMService:
    async def ask(self, question: str) -> dict:
        # 1. Embed query using Gemini
        query_embedding = await self._embed(question)
        # 2. pgvector similarity search
        summaries = self._search_similar(query_embedding, k=5)
        # 3. Build context from summaries
        context = self._build_context(summaries)
        # 4. Call OpenRouter with context + question
        answer = await self._chat(question, context)
        return {"answer": answer, "sources": [s.id for s in summaries]}
```

### 5. WebSocket Streaming

Refactor `backend/bomguard/api/ask.py` WebSocket endpoint:
- Accept question from client
- Run RAG pipeline
- Stream tokens from OpenRouter to client via WebSocket
- Send source citations at the end

### 6. Update REST Endpoint

Refactor `POST /api/ask` in `backend/bomguard/api/ask.py`:
- Accept `{"question": "..."}`
- Run RAG pipeline synchronously (non-streaming)
- Return `{"answer": "...", "sources": [...]}`

### 7. Frontend: Chat UI

Create `frontend/src/components/ask/ChatInterface.tsx`:
- Message list (user + assistant bubbles)
- Input field with send button
- Loading indicator while waiting
- Source citation pills below assistant messages
- Use React state for message history

For REST endpoint:
- Simple POST on send, append response to message list

For WebSocket (stretch goal):
- Connect on page mount
- Stream tokens as they arrive
- Show sources when stream completes

### 8. Frontend: Ask Page

Update `frontend/src/pages/AskPage.tsx`:
- Render `ChatInterface`
- Clean layout with sidebar

### 9. Seed Initial Summaries

Create a script or Celery task to backfill summaries for existing substances:
```bash
python -m bomguard.enrichment.tasks.generate_all_summaries
```

### 10. Tests

Backend:
- `test_openrouter_client.py` — mock HTTP responses, test streaming, test error handling
- `test_llm_service.py` — test RAG pipeline with mocked embeddings and chat
- `test_ask_api.py` — test REST endpoint, test WebSocket connection

Frontend:
- Component tests for ChatInterface (if testing setup exists)

### 11. Lint / Type-Check / Test

```bash
cd backend && ruff check . && mypy . && basedpyright . && pytest tests/
cd frontend && npm run lint && npm run typecheck && npm run build
```

## Key Files to Create/Modify

| Action | File |
|--------|------|
| Create | `backend/bomguard/services/openrouter_client.py` |
| Create | `backend/bomguard/services/summary_generator.py` |
| Create | `backend/bomguard/enrichment/summary_tasks.py` (Celery tasks) |
| Create | `backend/tests/test_services/test_openrouter_client.py` |
| Create | `backend/tests/test_api/test_ask_api.py` |
| Create | `frontend/src/components/ask/ChatInterface.tsx` |
| Modify | `backend/bomguard/services/llm_service.py` (full rewrite) |
| Modify | `backend/bomguard/api/ask.py` (full rewrite) |
| Modify | `frontend/src/pages/AskPage.tsx` |
| Modify | `backend/bomguard/celery_app.py` (add summary task) |
| Modify | `DECISIONS.md` (document dual-provider setup) |

## Notes for Parallel Agent
- **Embedding dimension is fixed at 768** (Gemini `text-embedding-004`). Do not change this without a migration.
- The `RegulatorySummary` table already exists with `embedding: Mapped[Vector(768)]`. Check the exact column name and model definition before writing queries.
- OpenRouter requires `HTTP-Referer` and `X-Title` headers. Use the GitHub repo URL or localhost for dev.
- Streaming via WebSocket is a stretch goal — get the REST endpoint working first.
- The summary generation task may be expensive (one LLM call per substance). Run it as a Celery task, not in the request path.
- The auth branch (`feat/auth-workos`) may add user sessions. If so, the Ask endpoint should eventually scope summaries to the user's subscribed regulations. For now, search all summaries.
