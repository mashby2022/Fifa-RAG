from abc import ABC, abstractmethod
import logging

import numpy as np

from app.core.config import settings
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
    def __init__(self, documents: list[WorldCupDocument]):
        try:
            from pymilvus import MilvusClient
        except ImportError as exc:
            raise RuntimeError("pymilvus is required when VECTOR_BACKEND=milvus.") from exc

        self.documents = documents
        self.documents_by_id = {doc.doc_id: doc for doc in documents}
        self.embedder = get_embedder()
        self.embedding_runtime_provider = self.embedder.__class__.__name__
        self.client = MilvusClient(uri=settings.milvus_uri)
        self.collection_name = settings.milvus_collection
        self._ensure_collection()

    @property
    def document_count(self) -> int:
        return len(self.documents)

    def _ensure_collection(self) -> None:
        if not self.client.has_collection(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=settings.embedding_dim,
                primary_field_name="id",
                vector_field_name="vector",
                id_type="string",
                metric_type="IP",
                auto_id=False,
            )
            self._insert_documents()

    def _insert_documents(self) -> None:
        batch_size = 64
        for start in range(0, len(self.documents), batch_size):
            batch = self.documents[start : start + batch_size]
            vectors = self.embedder.embed_many([doc.text for doc in batch], input_type="passage")
            self.client.insert(
                collection_name=self.collection_name,
                data=[{"id": doc.doc_id, "vector": vector} for doc, vector in zip(batch, vectors)],
            )

    def search(self, query: str, filters: dict[str, object], top_k: int) -> list[RetrievedDocument]:
        query_vector = self.embedder.embed(query, input_type="query")
        hits = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=max(top_k * 5, top_k),
            output_fields=["id"],
        )
        results: list[RetrievedDocument] = []
        for hit in hits[0]:
            doc_id = hit.get("id") or hit.get("entity", {}).get("id")
            doc = self.documents_by_id.get(doc_id)
            if not doc or not InMemoryVectorStore._matches_filters(doc, filters):
                continue
            vector_score = float(hit.get("distance", 0.0))
            score = vector_score + lexical_score(query, doc)
            results.append(RetrievedDocument(doc=doc, score=round(score, 4)))
            if len(results) >= top_k:
                break
        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]


def create_vector_store() -> VectorStore:
    documents = load_documents()
    if settings.vector_backend == "milvus":
        try:
            store = MilvusVectorStore(documents)
            setattr(store, "vector_runtime_backend", "milvus")
            return store
        except Exception as exc:
            logger.warning("Milvus initialization failed; falling back to in-memory vector store: %s", exc)
    store = InMemoryVectorStore(documents)
    setattr(store, "vector_runtime_backend", "memory")
    return store


vector_store = create_vector_store()
