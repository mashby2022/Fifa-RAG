from app.rag import vector_store as vector_store_module
from app.rag.embeddings import Embedder
from app.rag.mock_data import MOCK_DOCUMENTS
from app.rag.vector_store import InMemoryVectorStore


class BrokenEmbedder(Embedder):
    def embed(self, text: str, input_type: str = "query") -> list[float]:
        raise RuntimeError("embedding service rejected request")


def test_vector_store_falls_back_when_embedding_provider_fails(monkeypatch) -> None:
    monkeypatch.setattr(vector_store_module, "get_embedder", lambda: BrokenEmbedder())

    store = InMemoryVectorStore(MOCK_DOCUMENTS)
    results = store.search("Who won the 2014 final?", {}, 1)

    assert store.embedding_runtime_provider == "LocalHashEmbedder"
    assert results
