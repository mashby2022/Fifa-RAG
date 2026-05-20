# Deployment

Lovable hosts the frontend. This repo should be hosted as a separate backend API.

## Simple Path: Render

1. Push this repo to GitHub.
2. Create a new Render web service from the GitHub repo.
3. Render can use `render.yaml`, or you can configure manually:

```text
Build command: pip install -r requirements.txt
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

4. Set environment variables:

```text
APP_ENV=production
VECTOR_BACKEND=memory
EMBEDDING_PROVIDER=local_hash
GENERATOR_PROVIDER=extractive
CORS_ORIGINS=https://fifa-fan-chatter.lovable.app
```

5. Copy the Render service URL into Lovable:

```text
VITE_API_BASE_URL=https://your-render-service.onrender.com
```

## Container Path

Build:

```bash
docker build -t worldcup-rag-api .
```

Run:

```bash
docker run --env-file .env -p 8000:8000 worldcup-rag-api
```

## Production Notes

- Keep `VECTOR_BACKEND=memory` for the first hosted mock-data demo.
- Move to `VECTOR_BACKEND=milvus` once a hosted Milvus/Zilliz endpoint is available.
- Add the final Lovable domains to `CORS_ORIGINS`.
- Do not commit `.env` or partner raw datasets.
