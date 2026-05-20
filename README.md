# World Cup RAG Agent

A shareable FastAPI backend for a Lovable-hosted World Cup intelligence demo. The agent answers World Cup questions using structured football data, deterministic stats tools, semantic RAG evidence, optional Milvus retrieval, NVIDIA NIM generation, and Tavily web verification.

The experience is intentionally modeled after the Media Intelligence NAT demo: clear chat answers, visible worklog/tool routing, source chips, structured evidence, and failure-safe behavior when the data does not support an answer.

## Current Demo Status

This is no longer a mock-data shell. The backend now builds a real World Cup corpus from:

- Tom's delivered `raw/`, `processed/`, and `indexes/` bundles when present locally or provided as deploy-time zip URLs.
- `jfjelstul/worldcup` as the structured GitHub fallback.
- `openfootball/worldcup` for optional fixture and Football.TXT-style context.

The hosted demo uses a curated demo corpus by default:

```text
CORPUS_PROFILE=demo
DEMO_CORPUS_MAX_DOCS=1500
```

Use `CORPUS_PROFILE=full` to build the full corpus, which is currently about 6,611 generated documents from the available source tables.

## What It Can Do

- Answer grounded World Cup facts with citations.
- Route exact standings, team-finish, scorer, match-count, and schema questions to a DuckDB-style stats tool.
- Retrieve match, tournament, player, team, award, goal, schema, and article documents through the RAG layer.
- Handle follow-up workflows such as the 2022 final winner, opponent, score, penalties, referee, and referee assignments.
- Generate a World Cup match-map artifact for the 2022 tournament workflow.
- Verify prior grounded answers through Tavily web search when the user asks to check online.
- Explain invalid premises such as non-tournament years.
- Clarify club-versus-national-team mismatches.
- Expose `/api/architecture` for a frontend architecture page describing the NVIDIA and retrieval pipeline.

## Agent Architecture

```text
User question
  -> FastAPI chat endpoint
  -> query parser and guardrails
  -> deterministic tool router
      -> World Cup workflow tool
      -> DuckDB/statistics tool
      -> schema/codebook lookup
      -> Tavily web verification
  -> semantic RAG retrieval
      -> memory vector store today
      -> Milvus/Zilliz-ready backend
  -> optional NeMo Retriever reranking
  -> NVIDIA NIM or extractive generation
  -> grounded answer + citations + diagnostics
  -> Lovable frontend
```

The current implementation keeps routing deterministic for demo reliability. NAT can be added later as a higher-level orchestration layer, but this repo already exposes the tool pattern NAT would orchestrate.

## Data Layers

The document builder turns tabular data into multiple searchable story layers:

- `tournament`: host, dates, winner, runner-up, team count, tournament capsule.
- `match`: score, stage, venue, teams, outcome, scorers.
- `team`: tournament runs and team performance timelines.
- `standing`: final placements and standings summaries.
- `player`: appearances, squads, goals, awards, notable player profiles.
- `goal`: scorer records and tournament goal leaders.
- `award`: award winner cards.
- `schema`: codebook datasets and variables.
- `article`: optional local press/article text.
- `fixture`: optional OpenFootball fixture text.

This layered design keeps the demo from feeling like generic chat over CSVs.

## Important Demo Behaviors

These flows are currently supported and tested:

- `Who won the World Cup in 2022?`
- `Who did Argentina play in the 2022 final, and what was the score?`
- `Who refereed the 2022 final, and what other 2022 matches did they officiate?`
- `Create a map of the nations and head-to-head results for the 2022 World Cup.`
- `Which World Cup did Nigeria place the highest?`
- `Which World Cup did the Nigerian team place the highest?`
- `Which World Cup did USA women's place the highest?`
- `Check and find out.`
- `Which table tracks goals and goal scorers?`
- `Who won the World Cup in 2000?`
- `How did FC Barcelona perform in the 2014 World Cup?`

For “check and find out” style follow-ups, the agent uses the prior grounded answer to build a verification query instead of searching the literal low-information phrase.

## NVIDIA And Retrieval Stack

The repo is NeMo/NIM-aligned:

- `EMBEDDING_PROVIDER=nvidia` uses NVIDIA-hosted embedding APIs when available.
- If embedding calls fail at runtime, the backend falls back to `LocalHashEmbedder` so Render still serves the demo.
- `GENERATOR_PROVIDER=nvidia` uses an OpenAI-compatible NVIDIA NIM chat endpoint.
- `RERANKER_PROVIDER=nvidia` is wired for NeMo Retriever Reranking NIM, but the hosted demo currently keeps `RERANKER_PROVIDER=none`.
- `VECTOR_BACKEND=memory` is the default lightweight demo mode.
- `VECTOR_BACKEND=milvus` enables the Milvus adapter when a local or hosted Milvus/Zilliz endpoint is configured.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/ingest_dataset.py
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Run tests:

```bash
pytest
```

Run a smoke test:

```bash
python scripts/smoke_test_questions.py
```

## API

Health:

```http
GET /api/health
```

Demo prompts:

```http
GET /api/demo/questions
```

Tool status:

```http
GET /api/tools
```

Architecture content for the frontend:

```http
GET /api/architecture
```

Chat:

```http
POST /api/chat
Content-Type: application/json

{
  "message": "Which World Cup did USA women's place the highest?",
  "top_k": 5
}
```

Representative response:

```json
{
  "answer": "United States' highest World Cup finish in the women's tournament was champion, achieved at 1991 FIFA Women's World Cup, 1999 FIFA Women's World Cup, 2015 FIFA Women's World Cup, 2019 FIFA Women's World Cup.",
  "status": "grounded",
  "confidence": "high",
  "citations": [
    {
      "doc_id": "duckdb_stats:tournament_standings:57",
      "title": "duckdb_stats result from tournament_standings",
      "source_refs": [
        {
          "table": "tournament_standings",
          "record_id": "57"
        }
      ]
    }
  ],
  "tool_calls": [
    {
      "name": "duckdb_stats",
      "operation": "team_best_finish",
      "source_table": "tournament_standings"
    }
  ],
  "retrieval_diagnostics": {
    "tool_route": "duckdb_stats"
  }
}
```

## Environment Variables

Core hosted demo:

```text
PYTHON_VERSION=3.11.11
APP_ENV=production
AUTO_INGEST_ON_STARTUP=true
CORPUS_PROFILE=demo
DEMO_CORPUS_MAX_DOCS=1500
ENABLE_DUCKDB_TOOL=true
VECTOR_BACKEND=memory
EMBEDDING_PROVIDER=nvidia
GENERATOR_PROVIDER=nvidia
RERANKER_PROVIDER=none
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_EMBEDDING_MODEL=nvidia/nv-embedqa-e5-v5
NVIDIA_GENERATOR_MODEL=meta/llama-3.1-70b-instruct
NVIDIA_API_KEY=<set-in-render-only>
CORS_ORIGINS=https://fifa-fan-chatter.lovable.app,https://*.lovable.app,https://*.lovableproject.com
```

Optional Tavily web verification:

```text
WEB_SEARCH_ENABLED=true
WEB_SEARCH_PROVIDER=tavily
WEB_SEARCH_API_KEY=<set-in-render-only>
WEB_SEARCH_URL=https://api.tavily.com/search
```

Optional Milvus:

```text
VECTOR_BACKEND=milvus
MILVUS_URI=http://localhost:19530
MILVUS_COLLECTION=worldcup_docs
```

Optional reranking:

```text
RERANKER_PROVIDER=nvidia
NVIDIA_RERANKER_MODEL=nvidia/llama-nemotron-rerank-1b-v2
NVIDIA_RERANKER_URL=https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-nemotron-rerank-1b-v2/reranking
```

Never commit API keys or partner data bundles.

## Data Ingestion

The ingestion priority is:

```text
1. data/processed/{table}.parquet
2. data/raw/{table}.csv
3. GitHub fallback from jfjelstul/worldcup
4. mock fallback only if generated documents are unavailable
```

Tom's local bundle can be extracted as:

```bash
unzip -qo ~/Downloads/raw.zip -d data
unzip -qo ~/Downloads/processed.zip -d data
unzip -qo ~/Downloads/indexes.zip -d data
python scripts/ingest_dataset.py
```

Render can download deploy-time bundles with:

```text
DATA_BUNDLE_URL=https://.../tom-worldcup-data.zip
RAW_DATA_ZIP_URL=https://.../raw.zip
PROCESSED_DATA_ZIP_URL=https://.../processed.zip
INDEXES_DATA_ZIP_URL=https://.../indexes.zip
```

Render build command:

```text
pip install -r requirements.txt && python scripts/prepare_data_bundle.py && python scripts/ingest_dataset.py
```

The generated corpus lives at:

```text
data/generated_docs/worldcup_docs.jsonl
```

It is intentionally ignored by Git so the repo stays lightweight.

## Lovable Frontend

Set this in Lovable:

```text
VITE_API_BASE_URL=https://fifa-rag.onrender.com
```

The frontend should call:

- `/api/chat` for messages.
- `/api/demo/questions` for prompt chips.
- `/api/tools` for runtime tool status.
- `/api/architecture` for the architecture page.

See [docs/LOVABLE.md](docs/LOVABLE.md).

## Render Deployment

The deployed backend is designed for:

```text
GitHub repo -> Render web service -> Lovable frontend
```

Manual Render settings:

```text
Build command: pip install -r requirements.txt && python scripts/prepare_data_bundle.py && python scripts/ingest_dataset.py
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

After deploy, verify:

```bash
curl https://fifa-rag.onrender.com/api/health
```

Expected health highlights:

```json
{
  "ok": true,
  "corpus_profile": "demo",
  "document_count": 1500,
  "tools": {
    "duckdb_stats": {
      "available": true
    },
    "web_search": {
      "available": true
    }
  }
}
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Milvus

Run local Milvus:

```bash
docker compose up -d milvus
```

Set:

```text
VECTOR_BACKEND=milvus
MILVUS_URI=http://localhost:19530
MILVUS_COLLECTION=worldcup_docs
```

If Milvus cannot initialize, the app falls back to the memory vector store so the hosted demo can continue running.

## Repo Structure

```text
app/
  api/              FastAPI routes and architecture endpoint
  core/             settings and runtime config
  rag/              parser, tools, retrieval, generation, corpus builder
  schemas/          API and document models
data/
  raw/              local source tables, ignored except .gitkeep
  processed/        local parquet/DuckDB bundle, ignored
  generated_docs/   generated JSONL corpus, ignored
docs/
  ARCHITECTURE_PAGE.md
  DATA_CONTRACT.md
  DEPLOYMENT.md
  LOVABLE.md
  TOM_DATA.md
scripts/
  ingest_dataset.py
  prepare_data_bundle.py
  smoke_test_questions.py
tests/
  API, retrieval, stats, web-search, and workflow tests
```

## Development Notes

- Keep deterministic routes for high-stakes demo questions that require exact structured answers.
- Use RAG retrieval for story/context questions and evidence-card UX.
- Use Tavily web search as verification or live-context fallback, not as the primary source for historical World Cup facts.
- Keep `CORPUS_PROFILE=demo` for Render unless you move vectors into Milvus or cache embeddings.
- Use `/api/tools` and `/api/health` to inspect runtime behavior before debugging the Lovable frontend.
