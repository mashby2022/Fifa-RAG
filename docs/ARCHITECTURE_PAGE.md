# Architecture Page Content

Use this as the frontend architecture page for the Lovable app.

## Page Goal

Explain that the bot is not a generic chatbot. It is a layered World Cup intelligence RAG system using structured sports data, NeMo Retriever-style retrieval, NVIDIA NIM generation, and citation-first answer grounding.

## Suggested UI Layout

Add a top navigation item or segmented control:

```text
Chat | Architecture
```

The Architecture page should be compact, visual, and internal-demo friendly.

## Hero Copy

Title:

```text
World Cup Intelligence RAG Architecture
```

Subtitle:

```text
A NeMo Retriever and NVIDIA NIM powered assistant over structured World Cup data.
```

Supporting copy:

```text
The bot treats World Cup data as multiple searchable story layers rather than one flat pile of rows. Structured tables from Fjelstul World Cup and OpenFootball are transformed into human-readable documents for tournaments, matches, team runs, awards, and story arcs. Retrieval combines metadata filtering, semantic embeddings, hybrid scoring, optional Milvus vector storage, reranking, and grounded generation with citations.
```

## Main Pipeline

Render as a horizontal or vertical flow:

```text
Structured Data
  -> Story Layer Builder
  -> Query Understanding
  -> Hybrid Retrieval
  -> NeMo Reranking
  -> NVIDIA NIM Generation
  -> Answer + Citations
```

## Story Layers

Show these as compact cards:

- Tournament Capsules: host, dates, winner, overview.
- Match Narratives: score, venue, stage, result.
- Team Runs: stage reached, record, goals, tournament path.
- Awards And Player Signals: Golden Boot, Golden Ball, notable players.
- Fixture And Future Context: OpenFootball fixtures and schedule-oriented records.

## NVIDIA Technology Cards

Show four cards:

- NeMo Retriever Embeddings: semantic vectors for questions and World Cup story documents.
- NeMo Retriever Reranking NIM: reranks candidate evidence for precision.
- NVIDIA NIM Generation: grounded answer generation from selected evidence.
- Milvus-Ready Vector Store: scalable vector search target for the same document schema.

## API Endpoint

The backend exposes this content as structured JSON:

```http
GET /api/architecture
```

For this deployed backend:

```text
https://fifa-rag.onrender.com/api/architecture
```

## Lovable Prompt Add-On

Paste this into Lovable:

```text
Add an Architecture page to the existing World Cup RAG app.

Use a top-level tab or nav control with two views: Chat and Architecture.

Fetch architecture content from:
GET ${VITE_API_BASE_URL}/api/architecture

Render the Architecture page as a polished enterprise demo explainer. It should not feel like a marketing landing page. It should feel like a technical product walkthrough for NVIDIA / Lenovo / FIFA stakeholders.

Page structure:
- Header with title and subtitle from the API.
- Short overview paragraph.
- Pipeline section showing the mechanism from structured data ingestion through answer + citations.
- Story Layers section with cards for tournament capsules, match narratives, team runs, awards/player signals, and fixture/future context.
- NVIDIA Technologies section with cards for NeMo Retriever Embeddings, NeMo Retriever Reranking NIM, NVIDIA NIM Generation, and Milvus-ready vector storage.
- Demo Callouts section with concise bullets.

Design:
- Match the existing app style.
- Use compact cards, badges, and directional arrows.
- Keep it dense, clear, and inspection-friendly.
- Avoid a marketing hero and avoid decorative fluff.
- Make the NVIDIA technologies visibly connected to the bot mechanism.
```

