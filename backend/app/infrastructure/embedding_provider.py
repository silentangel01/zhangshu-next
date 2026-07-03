"""Embedding provider abstraction for knowledge chunk vectorization."""

import hashlib
from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding providers.

    An embedding provider converts text into fixed-dimensional vectors
    suitable for similarity search.
    """

    def encode(self, text: str) -> list[float]:
        """Encode a single text into a vector."""
        ...

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts into vectors."""
        ...

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        ...

    @property
    def vector_dim(self) -> int:
        """Return the output vector dimension."""
        ...


class BigramHashEmbeddingProvider:
    """Stub embedding provider using character bigram frequency hashing.

    Generates deterministic vectors based on character bigram statistics.
    Similar texts produce similar vectors through shared bigram patterns.
    Uses numpy for efficient vector operations.
    """

    VECTOR_DIM = 256
    # v2: switched from Python built-in hash() (unstable across processes
    # due to PYTHONHASHSEED randomisation) to hashlib.blake2b for deterministic
    # dimension mapping.  Old v1 vectors persisted in the database are no longer
    # compatible and will be reported as stale by the index-status API.
    MODEL_NAME = "bigram-hash-v2"

    @classmethod
    def _bigram_index(cls, bigram: str) -> int:
        """Map a bigram to a stable dimension index using blake2b.

        Do NOT use the Python built-in ``hash()`` here — its output changes
        across interpreter invocations when ``PYTHONHASHSEED`` is randomised,
        which would make persisted vectors inconsistent with fresh queries.
        """
        digest = hashlib.blake2b(bigram.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % cls.VECTOR_DIM

    def encode(self, text: str) -> list[float]:
        """Encode text using character bigram frequency hashing."""
        vector = np.zeros(self.VECTOR_DIM, dtype=np.float64)

        if not text or len(text) < 2:
            return vector.tolist()

        # Extract character bigrams and map to dimensions via stable hash
        for i in range(len(text) - 1):
            bigram = text[i : i + 2]
            idx = self._bigram_index(bigram)
            vector[idx] += 1.0

        # L2 normalize to unit vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts."""
        return [self.encode(text) for text in texts]

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    @property
    def vector_dim(self) -> int:
        return self.VECTOR_DIM


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a = np.array(vec_a, dtype=np.float64)
    b = np.array(vec_b, dtype=np.float64)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def cosine_similarity_batch(
    query: list[float], vectors: list[list[float]]
) -> list[float]:
    """Compute cosine similarity between a query vector and multiple vectors.

    Uses numpy vectorized operations for efficiency.
    """
    if not vectors:
        return []

    q = np.array(query, dtype=np.float64)
    v = np.array(vectors, dtype=np.float64)

    # Compute norms
    q_norm = np.linalg.norm(q)
    v_norms = np.linalg.norm(v, axis=1)

    if q_norm == 0:
        return [0.0] * len(vectors)

    # Avoid division by zero
    v_norms = np.where(v_norms == 0, 1.0, v_norms)

    # Compute similarities
    similarities = np.dot(v, q) / (q_norm * v_norms)

    # Zero out results where vector norm was zero
    zero_mask = np.linalg.norm(v, axis=1) == 0
    similarities[zero_mask] = 0.0

    return similarities.tolist()
