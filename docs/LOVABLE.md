# Lovable Frontend Integration

Use Lovable as the hosted frontend and point it at this FastAPI backend.

## Backend URLs

Local backend:

```text
http://127.0.0.1:8000
```

Production backend:

```text
https://your-backend-host.example.com
```

Set the frontend environment variable:

```text
VITE_API_BASE_URL=https://your-backend-host.example.com
```

## API Contract

Health:

```http
GET /api/health
```

Demo questions:

```http
GET /api/demo/questions
```

Chat:

```http
POST /api/chat
Content-Type: application/json

{
  "message": "Who won the men's World Cup in 2014?",
  "top_k": 5
}
```

Response:

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

## Lovable Prompt

Paste this into Lovable:

```text
Build a polished internal demo frontend for a World Cup RAG assistant.

Use a two-panel app layout, not a landing page.

Left panel:
- Chat interface.
- Preset question buttons from GET /api/demo/questions.
- User and assistant messages.
- Under assistant answers, show citation chips with doc title and table/record IDs.
- Use answer status badges: grounded, partial, no_answer, invalid_premise.

Right panel:
- Evidence/context panel for the latest response.
- Show top retrieved documents as compact cards.
- Each card should show title, entity type, tournament year, score, source refs, and whether it was used.
- Show applied filters and confidence.

API base URL comes from VITE_API_BASE_URL.
Endpoints:
- GET /api/health
- GET /api/demo/questions
- POST /api/chat with { "message": string, "top_k": number }

Design language:
- Clear, enterprise demo style inspired by NVIDIA internal demo tools.
- Dense but readable.
- No marketing hero.
- First screen is the working app.
- Make source evidence obvious without overwhelming the answer.
```

## CORS

Add your Lovable URLs to the backend `.env`:

```text
CORS_ORIGINS=https://fifa-fan-chatter.lovable.app
```

For your current Lovable app, set the frontend environment variable to your deployed backend URL:

```text
VITE_API_BASE_URL=https://your-backend-host.example.com
```

For example, after deploying on Render, this will look like:

```text
VITE_API_BASE_URL=https://worldcup-rag-api.onrender.com
```
