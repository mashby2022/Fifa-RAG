# World Cup RAG Agent 

A shareable, Lovable-ready backend for a NeMo/NIM-aligned World Cup RAG demo. The product bar is the Media Intelligence NAT demo: clear answers, visible evidence, simple frontend flow, and behavior reviewers can inspect.

The repo currently runs with mock World Cup data and a deterministic local retriever, so it is useful before the partner tabular datasets arrive. Milvus and NVIDIA provider boundaries are already represented in config and code so the shell can be upgraded without changing the frontend API contract.

## What This Demo Shows

- Grounded World Cup answers with citations.
- Source cards for the records behind each answer.
- Controlled no-answer behavior for invalid premises.
- A stable API contract for a Lovable-hosted frontend.
- A data contract for partner-provided tabular datasets.
- Agent-style tools for exact stats, schema inspection, article retrieval, and optional web fallback.
- A repo shape suitable for GitHub collaboration and CI.

## Architecture

```text
Partner tabular datasets
  -> normalization/document builder
  -> generated World Cup documents
  -> embeddings
  -> DuckDB stats tool + Milvus or local vector store
  -> retriever, optional web fallback, and optional reranker
  -> grounded response generator
  -> Lovable frontend
```

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Try:

```bash
python scripts/smoke_test_questions.py
```

Build the real-data document corpus from the upstream GitHub datasets:

```bash
python scripts/ingest_dataset.py
```

Run tests:

```bash
pytest
```

## API

Health:

```http
GET /api/health
```

Preset demo questions:

```http
GET /api/demo/questions
```

Tool status:

```http
GET /api/tools
```

Chat:

```http
POST /api/chat
Content-Type: application/json

{
  "message": "Who won the men's World Cup in 2014, and who did they beat in the final?",
  "top_k": 5
}
```

Response shape:

```json
{
  "answer": "Germany won the 2014 men's FIFA World Cup...",
  "status": "grounded",
  "confidence": "medium",
  "citations": [
    {
      "doc_id": "match:2014:final:germany-argentina",
      "title": "2014 FIFA World Cup Final: Germany vs Argentina",
      "source_refs": [
        {
          "table": "matches",
          "record_id": "mock-match-2014-final"
        }
      ]
    }
  ],
  "retrieved_context": [],
  "filters": {
    "competition": "men",
    "tournament_year": 2014
  }
}
```

## Lovable Frontend

Use [docs/LOVABLE.md](docs/LOVABLE.md) as the frontend integration spec. The key frontend environment variable is:

```text
VITE_API_BASE_URL=https://your-backend-host.example.com
```

The intended UI is a two-panel internal demo:

- Left: chat, preset questions, answers, citation chips.
- Right: evidence cards, retrieved context, filters, status, confidence.

This keeps the frontend easy to use while still making the RAG behavior inspectable.

## Hosting

Use [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Render or container deployment. The fastest shareable path is:

```text
GitHub repo -> Render backend -> Lovable frontend
```

For the first hosted demo, keep the backend in mock-data mode but use NVIDIA-hosted NIM for embeddings and generation:

```text
VECTOR_BACKEND=memory
EMBEDDING_PROVIDER=nvidia
GENERATOR_PROVIDER=nvidia
CORPUS_PROFILE=demo
DEMO_CORPUS_MAX_DOCS=1500
NVIDIA_API_KEY=<set-in-render-only>
```

No other key is required for the default demo. Add a Tavily key only if you enable `WEB_SEARCH_ENABLED=true`, and add a hosted Milvus/Zilliz URI/token only when moving beyond the in-memory vector store.

## Data Integration

Partner datasets should land in `data/raw/` and `data/processed/`, then be normalized into generated document records under `data/generated_docs/`.

See [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md).
See [docs/TOM_DATA.md](docs/TOM_DATA.md) for Tom's delivered bundle.

Current ingestion prefers Tom's local processed/raw files, then falls back to `jfjelstul/worldcup`:

```bash
python scripts/ingest_dataset.py
```

This writes generated documents to:

```text
data/generated_docs/worldcup_docs.jsonl
```

By default, ingestion writes a curated demo corpus capped at 1,500 documents. Set `CORPUS_PROFILE=full` to rebuild the complete corpus from the same source tables.

The generated corpus is intentionally ignored by Git. Render rebuilds it during deployment from:

- https://github.com/jfjelstul/worldcup
- https://github.com/openfootball/worldcup

## Agentic Tools

The backend now has lightweight equivalents of the backup ChainLit/NAT tool pattern:

- `duckdb_stats`: exact counts and grouped stats over `worldcup.duckdb`, local CSVs, or GitHub fallback tables.
- `duckdb_schema`: codebook/schema summaries when Tom's codebook files are available.
- `article_lookup`: local press/article text from `data/press/*.txt` or `data/press/*.md`.
- `web_search`: optional Tavily-backed fallback, disabled by default.
- `milvus_retrieval`: optional runtime backend when `VECTOR_BACKEND=milvus`.

## Milvus

Start local Milvus:

```bash
docker compose up -d milvus
```

Set:

```text
VECTOR_BACKEND=milvus
MILVUS_URI=http://localhost:19530
MILVUS_COLLECTION=worldcup_docs
```

The app will try the Milvus adapter when `VECTOR_BACKEND=milvus`; if Milvus cannot initialize, it falls back to the in-memory vector store so Render can still serve the demo.

## Repo Structure

```text
app/
  api/              FastAPI routes
  core/             settings and runtime config
  rag/              retrieval, parsing, mock data, generation
  schemas/          API and document contracts
data/
  raw/              partner source files
  normalized/       cleaned/intermediate tables
  generated_docs/   JSONL documents for indexing
docs/
  DATA_CONTRACT.md
  LOVABLE.md
scripts/
  ingest_dataset.py
  smoke_test_questions.py
tests/
  test_chat_api.py
  test_query_parser.py
```

## Demo-Ready Behaviors

The current shell supports:

- “Who won the men's World Cup in 2014, and who did they beat in the final?”
- “Which country hosted the 2018 World Cup?”
- “How did Argentina perform across the 2010, 2014, and 2018 World Cups?”
- “Who won the World Cup in 2000?”
- “How did FC Barcelona perform in the 2014 World Cup?”

These cover the main demo modes: grounded fact, summary, invalid year, and club-versus-country clarification.
