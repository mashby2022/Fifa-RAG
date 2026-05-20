from app.core.config import settings
from app.rag.generator import generate_answer
from app.rag.query_parser import parse_query
from app.rag.reranker import maybe_rerank
from app.rag.vector_store import vector_store
from app.schemas.api import ChatRequest, ChatResponse


class RagService:
    def answer(self, request: ChatRequest) -> ChatResponse:
        parsed = parse_query(request.message, request.query_mode)
        if parsed.invalid_reason:
            response = generate_answer(parsed, [])
            return self._with_diagnostics(response, parsed, 0, {"reranker": "skipped"})

        retrieval_query = parsed.query_rewrite or request.message
        initial_k = max(request.top_k, settings.initial_retrieval_k)
        candidates = vector_store.search(retrieval_query, parsed.filters, initial_k)
        retrieved, rerank_diagnostics = maybe_rerank(request.message, candidates, request.top_k)
        response = generate_answer(parsed, retrieved)
        return self._with_diagnostics(response, parsed, len(candidates), rerank_diagnostics)

    @property
    def document_count(self) -> int:
        return vector_store.document_count

    @staticmethod
    def _with_diagnostics(
        response: ChatResponse,
        parsed,
        initial_count: int,
        rerank_diagnostics: dict[str, object],
    ) -> ChatResponse:
        response.intent = parsed.intent
        response.query_rewrite = parsed.query_rewrite if parsed.query_rewrite != parsed.text else None
        response.layers_searched = parsed.layers
        response.retrieval_diagnostics = {
            "initial_retrieved": initial_count,
            "final_context": len(response.retrieved_context),
            "filters": parsed.filters,
            **rerank_diagnostics,
        }
        return response


rag_service = RagService()
