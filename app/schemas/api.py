from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.documents import AnswerStatus, RetrievedDocument, SourceRef


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)
    query_mode: Literal["auto", "matches", "teams", "players", "tournaments", "schema", "compare_eras", "articles"] = "auto"


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
    intent: str = "unknown"
    query_rewrite: str | None = None
    layers_searched: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, object]] = Field(default_factory=list)
    retrieval_diagnostics: dict[str, object] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    ok: bool
    app: str
    vector_backend: str
    vector_runtime_backend: str
    embedding_provider: str
    embedding_runtime_provider: str
    generator_provider: str
    reranker_provider: str
    nvidia_configured: bool
    corpus_profile: str
    demo_corpus_max_docs: int
    document_count: int
    tools: dict[str, object] = Field(default_factory=dict)


class ArchitectureStep(BaseModel):
    title: str
    description: str
    technologies: list[str]


class ArchitectureLayer(BaseModel):
    name: str
    purpose: str
    examples: list[str]


class ArchitectureResponse(BaseModel):
    title: str
    subtitle: str
    overview: str
    pipeline: list[ArchitectureStep]
    story_layers: list[ArchitectureLayer]
    nvidia_technologies: list[ArchitectureStep]
    demo_callouts: list[str]
