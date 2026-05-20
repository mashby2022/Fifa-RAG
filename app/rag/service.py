from app.rag.generator import generate_answer
from app.rag.query_parser import parse_query
from app.rag.vector_store import vector_store
from app.schemas.api import ChatRequest, ChatResponse


class RagService:
    def answer(self, request: ChatRequest) -> ChatResponse:
        parsed = parse_query(request.message)
        if parsed.invalid_reason:
            return generate_answer(parsed, [])
        retrieved = vector_store.search(request.message, parsed.filters, request.top_k)
        return generate_answer(parsed, retrieved)

    @property
    def document_count(self) -> int:
        return vector_store.document_count


rag_service = RagService()
