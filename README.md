# World Cup RAG Shell with Milvus

A shareable, Lovable-ready backend for a NeMo/NIM-aligned World Cup RAG demo. The product bar is the Media Intelligence NAT demo: clear answers, visible evidence, simple frontend flow, and behavior reviewers can inspect.

The repo currently runs with mock World Cup data and a deterministic local retriever, so it is useful before the partner tabular datasets arrive. Milvus and NVIDIA provider boundaries are already represented in config and code so the shell can be upgraded without changing the frontend API contract.

## What This Demo Shows

- Grounded World Cup answers with citations.
- Source cards for the records behind each answer.
- Controlled no-answer behavior for invalid premises.
- A stable API contract for a Lovable-hosted frontend.
- A data contract for partner-provided tabular datasets.
- A repo shape suitable for GitHub collaboration and CI.

## Architecture

```text
Partner tabular datasets
  -> normalization/document builder
  -> generated World Cup documents
  -> embeddings
  -> Milvus or local vector store
  -> retriever and optional reranker
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
NVIDIA_API_KEY=<set-in-render-only>
```

## Data Integration

Partner datasets should land in `data/raw/` and be normalized into generated document records under `data/generated_docs/`.

See [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md).

Current ingestion downloads from `jfjelstul/worldcup` and `openfootball/worldcup`:

```bash
python scripts/ingest_dataset.py
```

This writes generated documents to:

```text
data/generated_docs/worldcup_docs.jsonl
```

The generated corpus is intentionally ignored by Git. Render rebuilds it during deployment from:

- https://github.com/jfjelstul/worldcup
- https://github.com/openfootball/worldcup

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

The Milvus adapter is intentionally left as the next integration point. The current repo uses an in-memory vector store so the API and Lovable frontend can be built immediately.

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
