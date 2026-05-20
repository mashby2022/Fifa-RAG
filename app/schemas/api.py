from pydantic import BaseModel, Field

from app.schemas.documents import AnswerStatus, RetrievedDocument, SourceRef


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)


class Citation(BaseModel):
    doc_id: str
    title: str
    source_refs: list[SourceRef]


class ChatResponse(BaseModel):
    answer: str
    status: AnswerStatus
    confidence: str
    citations: list[Citation]
    retrieved_context: list[RetrievedDocument]
    filters: dict[str, object]


class HealthResponse(BaseModel):
    ok: bool
    app: str
    vector_backend: str
    embedding_provider: str

