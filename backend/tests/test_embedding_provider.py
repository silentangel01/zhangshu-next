"""Tests for the embedding provider infrastructure."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.embedding_provider import (  # noqa: E402
    BigramHashEmbeddingProvider,
    cosine_similarity,
    cosine_similarity_batch,
)


@pytest.fixture
def provider():
    return BigramHashEmbeddingProvider()


# ---------- Basic Properties ----------


class TestProviderProperties:
    def test_model_name(self, provider):
        assert provider.model_name == "bigram-hash-v1"

    def test_vector_dim(self, provider):
        assert provider.vector_dim == 256


# ---------- Encode ----------


class TestEncode:
    def test_output_dimension(self, provider):
        vector = provider.encode("这是一段测试文本")
        assert len(vector) == 256

    def test_same_text_same_vector(self, provider):
        v1 = provider.encode("相同的文本内容")
        v2 = provider.encode("相同的文本内容")
        assert v1 == v2

    def test_different_text_different_vector(self, provider):
        v1 = provider.encode("魔法体系")
        v2 = provider.encode("科技发展")
        assert v1 != v2

    def test_empty_text_zero_vector(self, provider):
        vector = provider.encode("")
        assert all(v == 0.0 for v in vector)

    def test_single_char_zero_vector(self, provider):
        vector = provider.encode("单")
        assert all(v == 0.0 for v in vector)

    def test_normalized_unit_vector(self, provider):
        vector = provider.encode("这是一段较长的测试文本用于验证归一化")
        arr = np.array(vector)
        norm = np.linalg.norm(arr)
        assert abs(norm - 1.0) < 1e-6

    def test_similar_texts_higher_similarity(self, provider):
        # Similar texts share bigrams
        v1 = provider.encode("魔法体系的详细说明")
        v2 = provider.encode("魔法体系的设定文档")
        v3 = provider.encode("完全不同的内容")

        sim_12 = cosine_similarity(v1, v2)
        sim_13 = cosine_similarity(v1, v3)

        # Texts sharing "魔法体系的" should be more similar
        assert sim_12 > sim_13


# ---------- Encode Batch ----------


class TestEncodeBatch:
    def test_batch_matches_individual(self, provider):
        texts = ["文本一", "文本二内容", "第三段文本"]
        batch_results = provider.encode_batch(texts)
        individual_results = [provider.encode(t) for t in texts]

        assert len(batch_results) == len(individual_results)
        for batch, individual in zip(batch_results, individual_results):
            assert batch == individual

    def test_empty_batch(self, provider):
        results = provider.encode_batch([])
        assert results == []


# ---------- Cosine Similarity ----------


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0, 1.0]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        assert abs(cosine_similarity(v1, v2)) < 1e-6

    def test_opposite_vectors(self):
        v1 = [1.0, 0.0]
        v2 = [-1.0, 0.0]
        assert abs(cosine_similarity(v1, v2) - (-1.0)) < 1e-6

    def test_zero_vector(self):
        v1 = [0.0, 0.0]
        v2 = [1.0, 0.0]
        assert cosine_similarity(v1, v2) == 0.0

    def test_batch_similarity(self):
        query = [1.0, 0.0, 0.0]
        vectors = [
            [1.0, 0.0, 0.0],  # identical -> 1.0
            [0.0, 1.0, 0.0],  # orthogonal -> 0.0
            [-1.0, 0.0, 0.0],  # opposite -> -1.0
        ]
        results = cosine_similarity_batch(query, vectors)
        assert len(results) == 3
        assert abs(results[0] - 1.0) < 1e-6
        assert abs(results[1]) < 1e-6
        assert abs(results[2] - (-1.0)) < 1e-6

    def test_batch_empty(self):
        results = cosine_similarity_batch([1.0, 0.0], [])
        assert results == []

    def test_batch_zero_query(self):
        results = cosine_similarity_batch([0.0, 0.0], [[1.0, 0.0], [0.0, 1.0]])
        assert all(r == 0.0 for r in results)
