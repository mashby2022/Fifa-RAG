import hashlib
import math
import re
from abc import ABC, abstractmethod

import httpx
import numpy as np

from app.core.config import settings

TOKEN_RE = re.compile(r"[a-z0-9]+")


class Embedder(ABC):
    @abstractmethod
    def embed(self, text: str, input_type: str = "query") -> list[float]:
        raise NotImplementedError


class LocalHashEmbedder(Embedder):
    """Deterministic local embedder for demos and tests.

    This keeps the repo runnable without external credentials. Production can
    swap this behind the same interface for NVIDIA embeddings.
    """

    def __init__(self, dim: int = settings.embedding_dim):
        self.dim = dim

    def embed(self, text: str, input_type: str = "query") -> list[float]:
        vector = np.zeros(self.dim, dtype=np.float32)
        tokens = TOKEN_RE.findall(text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(float(np.dot(vector, vector)))
        if norm == 0:
            return vector.tolist()
        return (vector / norm).tolist()


class NvidiaEmbedder(Embedder):
    def __init__(
        self,
        api_key: str = settings.nvidia_api_key,
        model: str = settings.nvidia_embedding_model,
        base_url: str = settings.nvidia_base_url,
        timeout_seconds: float = settings.nvidia_timeout_seconds,
    ):
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is required when EMBEDDING_PROVIDER=nvidia.")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def embed(self, text: str, input_type: str = "query") -> list[float]:
        payload = {
            "model": self.model,
            "input": [text],
            "input_type": input_type,
            "modality": "text",
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        response.raise_for_status()
        body = response.json()
        return body["data"][0]["embedding"]


def get_embedder() -> Embedder:
    if settings.embedding_provider == "nvidia":
        return NvidiaEmbedder()
    return LocalHashEmbedder()
