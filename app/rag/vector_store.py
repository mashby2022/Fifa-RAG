from abc import ABC, abstractmethod

import numpy as np

from app.rag.embeddings import embedder
from app.rag.mock_data import MOCK_DOCUMENTS
from app.schemas.documents import RetrievedDocument, WorldCupDocument


class VectorStore(ABC):
    @abstractmethod
    def search(self, query: str, filters: dict[str, object], top_k: int) -> list[RetrievedDocument]:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    def __init__(self, documents: list[WorldCupDocument]):
        self.documents = documents
        self.embeddings = {doc.doc_id: np.array(embedder.embed(doc.text), dtype=np.float32) for doc in documents}

    def search(self, query: str, filters: dict[str, object], top_k: int) -> list[RetrievedDocument]:
        query_vector = np.array(embedder.embed(query), dtype=np.float32)
        results: list[RetrievedDocument] = []
        for doc in self.documents:
            if not self._matches_filters(doc, filters):
                continue
            score = float(np.dot(query_vector, self.embeddings[doc.doc_id]))
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


class MilvusVectorStore(VectorStore):
    def search(self, query: str, filters: dict[str, object], top_k: int) -> list[RetrievedDocument]:
        raise NotImplementedError(
            "Milvus adapter placeholder: wire pymilvus here once the dataset and deployment target are finalized."
        )


vector_store = InMemoryVectorStore(MOCK_DOCUMENTS)

