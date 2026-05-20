import httpx

from app.core.config import settings
from app.schemas.documents import RetrievedDocument


class NvidiaReranker:
    def __init__(
        self,
        api_key: str = settings.nvidia_api_key,
        model: str = settings.nvidia_reranker_model,
        url: str = settings.nvidia_reranker_url,
        timeout_seconds: float = settings.nvidia_timeout_seconds,
    ):
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is required when RERANKER_PROVIDER=nvidia.")
        self.api_key = api_key
        self.model = model
        self.url = url
        self.timeout_seconds = timeout_seconds

    def rerank(self, query: str, candidates: list[RetrievedDocument], top_k: int) -> list[RetrievedDocument]:
        passages = [{"text": _passage_text(item)} for item in candidates]
        payload = {
            "model": self.model,
            "query": {"text": query},
            "passages": passages,
            "truncate": "END",
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
            )
        response.raise_for_status()
        body = response.json()
        rankings = body.get("rankings") or body.get("results") or body.get("data") or []
        reranked: list[RetrievedDocument] = []
        for result in rankings:
            index = result.get("index")
            if index is None or index >= len(candidates):
                continue
            item = candidates[index]
            item.rerank_score = float(result.get("logit", result.get("score", 0.0)))
            reranked.append(item)
        return reranked[:top_k] or candidates[:top_k]


def maybe_rerank(query: str, candidates: list[RetrievedDocument], top_k: int) -> tuple[list[RetrievedDocument], dict[str, object]]:
    if settings.reranker_provider != "nvidia":
        return candidates[:top_k], {"reranker": "none", "candidate_count": len(candidates), "reranked_count": 0}
    try:
        reranked = NvidiaReranker().rerank(query, candidates, top_k)
        return reranked, {
            "reranker": "nvidia",
            "reranker_model": settings.nvidia_reranker_model,
            "candidate_count": len(candidates),
            "reranked_count": len(reranked),
        }
    except Exception as exc:
        return candidates[:top_k], {
            "reranker": "nvidia_fallback",
            "reranker_error": exc.__class__.__name__,
            "candidate_count": len(candidates),
            "reranked_count": 0,
        }


def _passage_text(item: RetrievedDocument) -> str:
    return f"{item.doc.title}\n{item.doc.text}"[:2500]
