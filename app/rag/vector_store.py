from abc import ABC, abstractmethod
import re
import unicodedata
from typing import Any

import numpy as np

from app.rag.embeddings import get_embedder
from app.rag.document_loader import load_documents
from app.schemas.documents import RetrievedDocument, WorldCupDocument

TOKEN_RE = re.compile(r"[a-z0-9]+")
WIN_TOKENS = {"win", "winner", "won", "champion", "champions"}
HOST_TOKENS = {"host", "hosted", "hosting"}
FINAL_TOKENS = {"final", "finals"}
SCORER_TOKENS = {"scorer", "scored", "goals", "golden", "boot"}
SCHEMA_TOKENS = {"table", "dataset", "field", "column", "schema", "codebook", "variable"}
HERO_TOKENS = {"hero", "winner", "winning", "decisive"}


class VectorStore(ABC):
    @abstractmethod
    def search(self, query: str, filters: dict[str, object], top_k: int) -> list[RetrievedDocument]:
        raise NotImplementedError

    @property
    def document_count(self) -> int:
        return 0


class InMemoryVectorStore(VectorStore):
    def __init__(self, documents: list[WorldCupDocument]):
        self.documents = documents
        self.embedder = get_embedder()
        self.embeddings = self._embed_documents(documents)

    @property
    def document_count(self) -> int:
        return len(self.documents)

    def search(self, query: str, filters: dict[str, object], top_k: int) -> list[RetrievedDocument]:
        query_vector = np.array(self.embedder.embed(query, input_type="query"), dtype=np.float32)
        results: list[RetrievedDocument] = []
        for doc in self.documents:
            if not self._matches_filters(doc, filters):
                continue
            vector_score = float(np.dot(query_vector, self.embeddings[doc.doc_id]))
            score = vector_score + self._lexical_score(query, doc)
            results.append(RetrievedDocument(doc=doc, score=round(score, 4)))
        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]

    @staticmethod
    def _matches_filters(doc: WorldCupDocument, filters: dict[str, object]) -> bool:
        for key, value in filters.items():
            if value is None:
                continue
            if key == "competition" and doc.competition != value:
                return False
            if key == "tournament_year" and doc.tournament_year != value:
                return False
        return True

    def _embed_documents(self, documents: list[WorldCupDocument]) -> dict[str, np.ndarray]:
        embeddings: dict[str, np.ndarray] = {}
        batch_size = 64
        for start in range(0, len(documents), batch_size):
            batch = documents[start : start + batch_size]
            vectors = self.embedder.embed_many([doc.text for doc in batch], input_type="passage")
            embeddings.update(
                {doc.doc_id: np.array(vector, dtype=np.float32) for doc, vector in zip(batch, vectors)}
            )
        return embeddings

    @staticmethod
    def _lexical_score(query: str, doc: WorldCupDocument) -> float:
        normalized_query = _normalize_text(query)
        query_tokens = set(TOKEN_RE.findall(normalized_query))
        doc_text = " ".join(
            [
                doc.title,
                doc.text,
                _metadata_text(doc.metadata),
            ]
        )
        doc_text = _normalize_text(doc_text)
        doc_tokens = set(TOKEN_RE.findall(doc_text))

        overlap = len(query_tokens & doc_tokens)
        score = overlap * 0.08

        if str(doc.tournament_year) in query:
            score += 0.75
        if WIN_TOKENS & query_tokens:
            if doc.entity_type == "tournament":
                score += 0.45
            if doc.entity_type == "standing" and doc.metadata.get("position") == 1:
                score += 0.55
            if doc.entity_type == "match" and "won the match" in doc.text.lower():
                score += 0.25
        if HOST_TOKENS & query_tokens and doc.entity_type == "tournament":
            score += 0.7
        if FINAL_TOKENS & query_tokens:
            if doc.metadata.get("stage") == "final":
                score += 2.0
            if "final standings" in doc.title.lower():
                score += 0.4
        if HERO_TOKENS & query_tokens and doc.entity_type == "match" and doc.metadata.get("stage") == "final":
            score += 2.0
        if HERO_TOKENS & query_tokens and doc.entity_type == "award":
            score -= 0.4
        if SCORER_TOKENS & query_tokens and doc.entity_type == "award":
            score += 0.8
        if SCORER_TOKENS & query_tokens and doc.entity_type in {"goal", "player"}:
            score += 0.7
        if SCHEMA_TOKENS & query_tokens and doc.entity_type == "schema":
            score += 1.2
            if doc.metadata.get("doc_type") == "dataset":
                score += 1.4
            if doc.metadata.get("doc_type") == "variable":
                score -= 0.2
        if doc.entity_type == "team" and any(str(year) in query for year in doc.metadata.get("years", [])):
            score += 0.8
        query_years = {int(year) for year in re.findall(r"\b(19[0-9]{2}|20[0-9]{2})\b", query)}
        doc_years = set(doc.metadata.get("years", [])) if isinstance(doc.metadata.get("years"), list) else {doc.tournament_year}
        if len(query_years) > 1:
            if doc.entity_type == "team":
                score += 1.5
            else:
                score -= 0.5
            if query_years.issubset(doc_years):
                score += 2.0
        team = doc.metadata.get("team")
        if isinstance(team, str) and _normalize_text(team) in normalized_query:
            score += 2.0
        player = doc.metadata.get("player")
        if isinstance(player, str) and _normalize_text(player) in normalized_query:
            score += 2.0
        dataset = doc.metadata.get("dataset")
        if isinstance(dataset, str) and _normalize_text(dataset) in normalized_query:
            score += 3.0 if doc.metadata.get("doc_type") == "dataset" else 1.5
        variable = doc.metadata.get("variable")
        if isinstance(variable, str) and _normalize_text(variable) in normalized_query:
            score += 1.5
        teams = doc.metadata.get("teams")
        if isinstance(teams, list):
            score += sum(0.45 for team_name in teams if isinstance(team_name, str) and _normalize_text(team_name) in normalized_query)

        return score


def _metadata_text(metadata: dict[str, Any]) -> str:
    values: list[str] = []
    for value in metadata.values():
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        else:
            values.append(str(value))
    return " ".join(values)


def _normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


class MilvusVectorStore(VectorStore):
    def search(self, query: str, filters: dict[str, object], top_k: int) -> list[RetrievedDocument]:
        raise NotImplementedError(
            "Milvus adapter placeholder: wire pymilvus here once the dataset and deployment target are finalized."
        )


vector_store = InMemoryVectorStore(load_documents())
