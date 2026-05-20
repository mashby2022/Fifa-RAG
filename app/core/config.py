from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "World Cup RAG Shell"
    app_env: str = "local"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000,https://*.lovable.app,https://*.lovableproject.com"
    )

    vector_backend: str = "memory"
    milvus_uri: str = "http://localhost:19530"
    milvus_collection: str = "worldcup_docs"
    generated_docs_path: str = "data/generated_docs/worldcup_docs.jsonl"
    local_data_dir: str = "data"
    corpus_profile: str = "demo"
    demo_corpus_max_docs: int = 1500
    include_openfootball_docs: bool = False
    auto_ingest_on_startup: bool = False
    initial_retrieval_k: int = 30

    embedding_provider: str = "local_hash"
    embedding_dim: int = 384
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_timeout_seconds: float = 30.0
    nvidia_embedding_model: str = "nvidia/nv-embedqa-e5-v5"

    generator_provider: str = "extractive"
    nvidia_generator_model: str = "meta/llama-3.1-70b-instruct"
    reranker_provider: str = "none"
    nvidia_reranker_model: str = "nvidia/llama-nemotron-rerank-1b-v2"
    nvidia_reranker_url: str = "https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-nemotron-rerank-1b-v2/reranking"

    @cached_property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if "*" not in origin and origin.strip()]

    @cached_property
    def cors_origin_regex(self) -> str | None:
        wildcard_origins = [origin.strip() for origin in self.cors_origins.split(",") if "*" in origin]
        if not wildcard_origins:
            return None
        escaped = [origin.replace(".", r"\.").replace("*", r".*") for origin in wildcard_origins]
        return "^(" + "|".join(escaped) + ")$"


settings = Settings()
