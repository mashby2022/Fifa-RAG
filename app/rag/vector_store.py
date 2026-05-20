from abc import ABC, abstractmethod
import logging

import numpy as np

from app.rag.embeddings import LocalHashEmbedder, get_embedder
from app.rag.document_loader import load_documents
from app.rag.scoring import lexical_score
from app.schemas.documents import RetrievedDocument, WorldCupDocument

logger = logging.getLogger(__name__)


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
        self.embedding_runtime_provider = self.embedder.__class__.__name__
        self.embeddings = self._embed_documents(documents)

    @property
    def document_count(self) -> int:
        return len(self.documents)

    def search(self, query: str, filters: dict[str, object], top_k: int) -> list[RetrievedDocument]:
        query_vector = np.array(self._embed_query(query), dtype=np.float32)
        results: list[RetrievedDocument] = []
        for doc in self.documents:
            if not self._matches_filters(doc, filters):
                continue
            vector_score = float(np.dot(query_vector, self.embeddings[doc.doc_id]))
            score = vector_score + lexical_score(query, doc)
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
            if key == "entity_types" and isinstance(value, list) and doc.entity_type not in value:
                return False
        return True

    def _embed_documents(self, documents: list[WorldCupDocument]) -> dict[str, np.ndarray]:
        try:
            return self._embed_documents_with_current_provider(documents)
        except Exception as exc:
            logger.warning("Primary embedding provider failed; falling back to LocalHashEmbedder: %s", exc)
            self.embedder = LocalHashEmbedder()
            self.embedding_runtime_provider = self.embedder.__class__.__name__
            return self._embed_documents_with_current_provider(documents)

    def _embed_documents_with_current_provider(self, documents: list[WorldCupDocument]) -> dict[str, np.ndarray]:
        embeddings: dict[str, np.ndarray] = {}
        batch_size = 64
        for start in range(0, len(documents), batch_size):
            batch = documents[start : start + batch_size]
            vectors = self.embedder.embed_many([doc.text for doc in batch], input_type="passage")
            embeddings.update(
                {doc.doc_id: np.array(vector, dtype=np.float32) for doc, vector in zip(batch, vectors)}
            )
        return embeddings

    def _embed_query(self, query: str) -> list[float]:
        try:
            return self.embedder.embed(query, input_type="query")
        except Exception as exc:
            logger.warning("Query embedding failed; rebuilding local embeddings: %s", exc)
            self.embedder = LocalHashEmbedder()
            self.embedding_runtime_provider = self.embedder.__class__.__name__
            self.embeddings = self._embed_documents_with_current_provider(self.documents)
            return self.embedder.embed(query, input_type="query")


class MilvusVectorStore(VectorStore):
    def search(self, query: str, filters: dict[str, object], top_k: int) -> list[RetrievedDocument]:
        raise NotImplementedError(
            "Milvus adapter placeholder: wire pymilvus here once the dataset and deployment target are finalized."
        )


vector_store = InMemoryVectorStore(load_documents())
