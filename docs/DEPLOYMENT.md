# Deployment

Lovable hosts the frontend. This repo should be hosted as a separate backend API.

## Simple Path: Render

1. Push this repo to GitHub.
2. Create a new Render web service from the GitHub repo.
3. Render can use `render.yaml`, or you can configure manually:

```text
Build command: pip install -r requirements.txt && python scripts/prepare_data_bundle.py && python scripts/ingest_dataset.py
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

4. Set environment variables:

```text
PYTHON_VERSION=3.11.11
APP_ENV=production
AUTO_INGEST_ON_STARTUP=true
VECTOR_BACKEND=memory
EMBEDDING_PROVIDER=nvidia
GENERATOR_PROVIDER=nvidia
RERANKER_PROVIDER=none
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_EMBEDDING_MODEL=nvidia/nv-embedqa-e5-v5
NVIDIA_GENERATOR_MODEL=meta/llama-3.1-70b-instruct
NVIDIA_RERANKER_MODEL=nvidia/llama-nemotron-rerank-1b-v2
NVIDIA_RERANKER_URL=https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-nemotron-rerank-1b-v2/reranking
NVIDIA_API_KEY=<your-nvidia-nim-key>
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

- Keep `VECTOR_BACKEND=memory` for the first hosted data demo.
- Keep `CORPUS_PROFILE=demo` and `DEMO_CORPUS_MAX_DOCS=1500` for the lean Lovable/Render demo. Use `CORPUS_PROFILE=full` when Milvus or cached embeddings are ready.
- Tom's local data bundle is not committed to Git. For Render, use the GitHub fallback until Phase 5 packages the data as a release artifact or object-store download.
- To deploy Tom's bundle, set `DATA_BUNDLE_URL` to a zip containing `raw/` and/or `processed/`, or set `RAW_DATA_ZIP_URL`, `PROCESSED_DATA_ZIP_URL`, and `INDEXES_DATA_ZIP_URL` separately.
- Set `RERANKER_PROVIDER=nvidia` when you are ready to use NeMo Retriever Reranking NIM.
- Move to `VECTOR_BACKEND=milvus` once a hosted Milvus/Zilliz endpoint is available.
- Add the final Lovable domains to `CORS_ORIGINS`.
- Store `NVIDIA_API_KEY` only in Render, never in Lovable or GitHub.
- Do not commit `.env` or partner raw datasets.
- After deployment, `/api/health` should show `corpus_profile: "demo"` and `document_count: 1500`.
