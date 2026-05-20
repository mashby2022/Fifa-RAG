from app.core.config import settings
from app.rag.generator import generate_answer
from app.rag.query_parser import parse_query
from app.rag.reranker import maybe_rerank
from app.rag.tools.stats import ToolAnswer, stats_tool
from app.rag.tools.web_search import web_search_tool
from app.rag.tools.worldcup_workflow import worldcup_workflow_tool
from app.rag.vector_store import vector_store
from app.schemas.api import ChatRequest, ChatResponse, Citation
from app.schemas.documents import SourceRef


class RagService:
    def answer(self, request: ChatRequest) -> ChatResponse:
        parsed = parse_query(request.message, request.query_mode)
        if parsed.invalid_reason:
            response = generate_answer(parsed, [])
            return self._with_diagnostics(response, parsed, 0, {"reranker": "skipped"})

        workflow_answer = worldcup_workflow_tool.maybe_answer(request.message)
        if workflow_answer:
            response = self._tool_response(parsed, workflow_answer)
            return self._with_diagnostics(response, parsed, 0, {"reranker": "skipped", "tool_route": workflow_answer.tool_name})

        tool_answer = stats_tool.maybe_answer(request.message)
        if tool_answer:
            response = self._tool_response(parsed, tool_answer)
            return self._with_diagnostics(response, parsed, 0, {"reranker": "skipped", "tool_route": tool_answer.tool_name})

        retrieval_query = parsed.query_rewrite or request.message
        initial_k = max(request.top_k, settings.initial_retrieval_k)
        candidates = vector_store.search(retrieval_query, parsed.filters, initial_k)
        if not candidates:
            web_answer = web_search_tool.maybe_answer(request.message)
            if web_answer:
                response = self._tool_response(parsed, web_answer)
                return self._with_diagnostics(response, parsed, 0, {"reranker": "skipped", "tool_route": web_answer.tool_name})
        retrieved, rerank_diagnostics = maybe_rerank(request.message, candidates, request.top_k)
        response = generate_answer(parsed, retrieved)
        return self._with_diagnostics(response, parsed, len(candidates), rerank_diagnostics)

    @property
    def document_count(self) -> int:
        return vector_store.document_count

    @property
    def embedding_runtime_provider(self) -> str:
        return getattr(vector_store, "embedding_runtime_provider", "unknown")

    @property
    def vector_runtime_backend(self) -> str:
        return getattr(vector_store, "vector_runtime_backend", settings.vector_backend)

    @property
    def tool_status(self) -> dict[str, object]:
        return {
            "duckdb_stats": {"available": stats_tool.available, "backend": stats_tool.backend},
            "worldcup_workflow": {"available": stats_tool.available, "backend": stats_tool.backend},
            "milvus_retrieval": {
                "configured": settings.vector_backend == "milvus",
                "runtime_backend": self.vector_runtime_backend,
                "collection": settings.milvus_collection,
            },
            "web_search": {
                "available": web_search_tool.available,
                "enabled": settings.web_search_enabled,
                "provider": settings.web_search_provider,
                "last_error": web_search_tool.last_error,
            },
        }

    @staticmethod
    def _tool_response(parsed, tool_answer: ToolAnswer) -> ChatResponse:
        citations = [
            Citation(
                doc_id=f"{tool_answer.tool_name}:{citation['table']}:{citation['record_id']}",
                title=f"{tool_answer.tool_name} result from {citation['table']}",
                source_refs=[SourceRef(table=citation["table"], record_id=citation["record_id"])],
            )
            for citation in tool_answer.citations
        ]
        return ChatResponse(
            answer=tool_answer.answer,
            status="grounded",
            confidence="high",
            citations=citations,
            retrieved_context=[],
            filters=parsed.filters,
            tool_calls=[{"name": tool_answer.tool_name, **tool_answer.diagnostics}],
            agent_worklog=tool_answer.worklog,
            artifacts=tool_answer.artifacts,
        )

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
