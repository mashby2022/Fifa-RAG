from typing import Any, Literal

from pydantic import BaseModel, Field


EntityType = Literal["match", "team", "player", "tournament", "award", "standing", "goal", "schema", "article"]
AnswerStatus = Literal["grounded", "partial", "no_answer", "invalid_premise"]


class SourceRef(BaseModel):
    table: str
    record_id: str


class WorldCupDocument(BaseModel):
    doc_id: str
    entity_type: EntityType
    competition: Literal["men", "women"]
    tournament_year: int
    title: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[SourceRef]


class RetrievedDocument(BaseModel):
    doc: WorldCupDocument
    score: float
    rerank_score: float | None = None
    used: bool = False
