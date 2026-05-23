"""Vector store abstraction for knowledge chunk embedding storage and retrieval."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
from uuid import uuid4

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_embedding import KnowledgeEmbedding
from app.models.knowledge_source import KnowledgeSource


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class VectorSearchResult:
    """Result from a vector similarity search."""

    chunk_id: str
    source_id: str
    score: float
    source_type: str
    source_credibility: str


@runtime_checkable
class VectorStore(Protocol):
    """Protocol for vector stores.

    A vector store manages embedding persistence and similarity search.
    """

    def upsert(
        self,
        chunk_id: str,
        source_id: str,
        project_id: str,
        vector: list[float],
        model_name: str,
        vector_dim: int,
    ) -> None:
        """Insert or update an embedding for a chunk."""
        ...

    def delete(self, chunk_id: str) -> None:
        """Delete embedding for a chunk."""
        ...

    def delete_by_source(self, source_id: str) -> None:
        """Delete all embeddings for a source."""
        ...

    def search(
        self,
        query_vector: list[float],
        project_id: str,
        filters: dict | None = None,
        top_k: int = 20,
    ) -> list[VectorSearchResult]:
        """Search for similar chunks by vector similarity."""
        ...


class SqliteVectorStore:
    """SQLite-backed vector store using numpy for similarity computation.

    Stores vectors as JSON in the knowledge_embeddings table.
    Performs brute-force cosine similarity search with numpy vectorization.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(
        self,
        chunk_id: str,
        source_id: str,
        project_id: str,
        vector: list[float],
        model_name: str,
        vector_dim: int,
    ) -> None:
        """Insert or update an embedding for a chunk."""
        # Check if embedding already exists
        stmt = select(KnowledgeEmbedding).where(
            KnowledgeEmbedding.chunk_id == chunk_id
        )
        existing = self.db.scalar(stmt)

        vector_json = json.dumps(vector)
        now = utc_now()

        if existing:
            existing.vector_json = vector_json
            existing.model_name = model_name
            existing.vector_dim = vector_dim
            existing.updated_at = now
        else:
            embedding = KnowledgeEmbedding(
                id=str(uuid4()),
                project_id=project_id,
                chunk_id=chunk_id,
                source_id=source_id,
                model_name=model_name,
                vector_dim=vector_dim,
                vector_json=vector_json,
                created_at=now,
                updated_at=now,
            )
            self.db.add(embedding)

        self.db.commit()

    def delete(self, chunk_id: str) -> None:
        """Delete embedding for a chunk."""
        stmt = delete(KnowledgeEmbedding).where(
            KnowledgeEmbedding.chunk_id == chunk_id
        )
        self.db.execute(stmt)
        self.db.commit()

    def delete_by_source(self, source_id: str) -> None:
        """Delete all embeddings for a source."""
        stmt = delete(KnowledgeEmbedding).where(
            KnowledgeEmbedding.source_id == source_id
        )
        self.db.execute(stmt)
        self.db.commit()

    def search(
        self,
        query_vector: list[float],
        project_id: str,
        filters: dict | None = None,
        top_k: int = 20,
    ) -> list[VectorSearchResult]:
        """Search for similar chunks by cosine similarity.

        Args:
            query_vector: The query embedding vector.
            project_id: Project to search within.
            filters: Optional metadata filters (source_type, credibility, tag).
            top_k: Maximum number of results to return.

        Returns:
            List of VectorSearchResult sorted by similarity score descending.
        """
        # Build query: embeddings JOIN chunks JOIN sources
        stmt = (
            select(
                KnowledgeEmbedding.chunk_id,
                KnowledgeEmbedding.source_id,
                KnowledgeEmbedding.vector_json,
                KnowledgeSource.source_type,
                KnowledgeSource.credibility,
            )
            .join(
                KnowledgeChunk,
                KnowledgeEmbedding.chunk_id == KnowledgeChunk.id,
            )
            .join(
                KnowledgeSource,
                KnowledgeEmbedding.source_id == KnowledgeSource.id,
            )
            .where(KnowledgeEmbedding.project_id == project_id)
            .where(KnowledgeChunk.deleted_at.is_(None))
            .where(KnowledgeSource.deleted_at.is_(None))
        )

        # Apply metadata filters
        if filters:
            if filters.get("source_type"):
                stmt = stmt.where(KnowledgeSource.source_type == filters["source_type"])
            if filters.get("credibility"):
                stmt = stmt.where(
                    KnowledgeSource.credibility == filters["credibility"]
                )
            if filters.get("tag"):
                stmt = stmt.where(
                    KnowledgeSource.tags.ilike(f"%{filters['tag']}%")
                )
            if filters.get("source_id"):
                stmt = stmt.where(
                    KnowledgeEmbedding.source_id == filters["source_id"]
                )

        rows = self.db.execute(stmt).all()

        if not rows:
            return []

        # Prepare data for vectorized similarity computation
        chunk_ids = [row[0] for row in rows]
        source_ids = [row[1] for row in rows]
        vectors = [json.loads(row[2]) for row in rows]
        source_types = [row[3] for row in rows]
        credibilities = [row[4] for row in rows]

        # Compute cosine similarities using numpy
        q = np.array(query_vector, dtype=np.float64)
        v = np.array(vectors, dtype=np.float64)

        q_norm = np.linalg.norm(q)
        v_norms = np.linalg.norm(v, axis=1)

        if q_norm == 0:
            return []

        # Avoid division by zero
        v_norms_safe = np.where(v_norms == 0, 1.0, v_norms)
        similarities = np.dot(v, q) / (q_norm * v_norms_safe)

        # Zero out results where vector norm was zero
        zero_mask = v_norms == 0
        similarities[zero_mask] = 0.0

        # Get top-k indices sorted by similarity descending
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            results.append(
                VectorSearchResult(
                    chunk_id=chunk_ids[idx],
                    source_id=source_ids[idx],
                    score=score,
                    source_type=source_types[idx],
                    source_credibility=credibilities[idx],
                )
            )

        return results
