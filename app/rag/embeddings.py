import hashlib
import math
import re

import numpy as np

from app.core.config import settings

TOKEN_RE = re.compile(r"[a-z0-9]+")


class LocalHashEmbedder:
    """Deterministic local embedder for demos and tests.

    This keeps the repo runnable without external credentials. Production can
    swap this behind the same interface for NVIDIA embeddings.
    """

    def __init__(self, dim: int = settings.embedding_dim):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
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


embedder = LocalHashEmbedder()

