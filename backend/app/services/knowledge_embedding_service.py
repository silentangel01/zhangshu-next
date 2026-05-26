"""Knowledge embedding service for managing chunk vector indices."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.embedding_provider import (
    BigramHashEmbeddingProvider,
    EmbeddingProvider,
)
from app.infrastructure.embedding_provider_factory import (
    create_provider,
    get_default_provider,
    get_default_provider_id,
)
from app.infrastructure.vector_store import SqliteVectorStore, VectorStore
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_embedding import KnowledgeEmbedding
from app.models.knowledge_source import KnowledgeSource
from app.repositories.knowledge_index_profile_repo import KnowledgeIndexProfileRepository
from app.repositories.project_repo import ProjectRepository


# --- Exceptions ---


class EmbeddingProjectNotFoundError(Exception):
    pass


class EmbeddingSourceNotFoundError(Exception):
    pass


class EmbeddingChunkNotFoundError(Exception):
    pass


class ProviderMismatchError(Exception):
    """Raised when requested provider conflicts with existing project profile."""


# --- Response types ---


@dataclass
class IndexStatus:
    total_chunks: int
    indexed_chunks: int
    unindexed_chunks: int
    model_name: str
    provider_id: str | None = None
    provider_type: str | None = None
    display_name: str | None = None
    vector_dim: int | None = None
    chunk_size: str | None = None
    profile_status: str = "not_configured"
    last_refreshed_at: str | None = None
    last_error: str | None = None


# --- Service ---


class KnowledgeEmbeddingService:
    """Manages chunk embedding generation, storage, and index lifecycle."""

    def __init__(
        self,
        db: Session,
        provider: EmbeddingProvider | None = None,
        store: VectorStore | None = None,
    ):
        self.db = db
        self.provider = provider or BigramHashEmbeddingProvider()
        self.store = store or SqliteVectorStore(db)
        self.project_repo = ProjectRepository(db)
        self.profile_repo = KnowledgeIndexProfileRepository(db)
        self._explicit_provider = provider is not None

    def index_source(self, source_id: str) -> int:
        """Generate embeddings for all active chunks of a source.

        Returns the number of chunks indexed.
        """
        source = self._get_active_source(source_id)
        chunks = self._get_active_chunks(source_id)

        if not chunks:
            return 0

        count = 0
        for chunk in chunks:
            text = self._build_chunk_text(chunk, source)
            vector = self.provider.encode(text)
            self.store.upsert(
                chunk_id=chunk.id,
                source_id=source_id,
                project_id=source.project_id,
                vector=vector,
                model_name=self.provider.model_name,
                vector_dim=self.provider.vector_dim,
            )
            count += 1

        return count

    def index_chunk(self, chunk_id: str) -> None:
        """Generate embedding for a single chunk."""
        chunk = self._get_active_chunk(chunk_id)
        if chunk is None:
            raise EmbeddingChunkNotFoundError

        source = self._get_active_source(chunk.source_id)
        text = self._build_chunk_text(chunk, source)
        vector = self.provider.encode(text)
        self.store.upsert(
            chunk_id=chunk.id,
            source_id=chunk.source_id,
            project_id=chunk.project_id,
            vector=vector,
            model_name=self.provider.model_name,
            vector_dim=self.provider.vector_dim,
        )

    def rebuild_project_index(self, project_id: str) -> int:
        """Rebuild embeddings for all active chunks in a project.

        Returns the total number of chunks indexed.
        """
        self._ensure_project_exists(project_id)

        # Delete existing embeddings for this project
        self._delete_project_embeddings(project_id)

        # Get all active chunks in the project
        stmt = (
            select(KnowledgeChunk)
            .join(
                KnowledgeSource,
                KnowledgeChunk.source_id == KnowledgeSource.id,
            )
            .where(KnowledgeChunk.project_id == project_id)
            .where(KnowledgeChunk.deleted_at.is_(None))
            .where(KnowledgeSource.deleted_at.is_(None))
        )
        chunks = list(self.db.scalars(stmt).all())

        if not chunks:
            return 0

        # Build source cache to avoid repeated queries
        source_ids = {chunk.source_id for chunk in chunks}
        sources: dict[str, KnowledgeSource] = {}
        for sid in source_ids:
            source = self._get_active_source(sid)
            sources[sid] = source

        # Generate embeddings
        count = 0
        for chunk in chunks:
            source = sources[chunk.source_id]
            text = self._build_chunk_text(chunk, source)
            vector = self.provider.encode(text)
            self.store.upsert(
                chunk_id=chunk.id,
                source_id=chunk.source_id,
                project_id=project_id,
                vector=vector,
                model_name=self.provider.model_name,
                vector_dim=self.provider.vector_dim,
            )
            count += 1

        return count

    def get_index_status(self, project_id: str) -> IndexStatus:
        """Get embedding index status for a project."""
        self._ensure_project_exists(project_id)

        # Read profile for provider info
        profile = self.profile_repo.get_by_project(project_id)

        # Count total active chunks
        total_stmt = (
            select(func.count(KnowledgeChunk.id))
            .join(
                KnowledgeSource,
                KnowledgeChunk.source_id == KnowledgeSource.id,
            )
            .where(KnowledgeChunk.project_id == project_id)
            .where(KnowledgeChunk.deleted_at.is_(None))
            .where(KnowledgeSource.deleted_at.is_(None))
        )
        total_chunks = self.db.scalar(total_stmt) or 0

        # Count indexed chunks — filter by profile model if available
        indexed_stmt = select(func.count(KnowledgeEmbedding.id)).where(
            KnowledgeEmbedding.project_id == project_id
        )
        if profile is not None:
            indexed_stmt = indexed_stmt.where(
                KnowledgeEmbedding.model_name == profile.model_name
            ).where(
                KnowledgeEmbedding.vector_dim == profile.vector_dim
            )
        indexed_chunks = self.db.scalar(indexed_stmt) or 0

        if profile is not None:
            last_refreshed_str = None
            if profile.last_refreshed_at is not None:
                last_refreshed_str = profile.last_refreshed_at.isoformat()
            return IndexStatus(
                total_chunks=total_chunks,
                indexed_chunks=indexed_chunks,
                unindexed_chunks=max(0, total_chunks - indexed_chunks),
                model_name=profile.model_name,
                provider_id=profile.provider_id,
                provider_type=profile.provider_type,
                display_name=profile.display_name,
                vector_dim=profile.vector_dim,
                chunk_size=profile.chunk_size,
                profile_status=profile.status or "ready",
                last_refreshed_at=last_refreshed_str,
                last_error=profile.last_error,
            )

        return IndexStatus(
            total_chunks=total_chunks,
            indexed_chunks=indexed_chunks,
            unindexed_chunks=max(0, total_chunks - indexed_chunks),
            model_name=self.provider.model_name,
        )

    def remove_source_embeddings(self, source_id: str) -> None:
        """Remove all embeddings for a source."""
        self.store.delete_by_source(source_id)

    def resolve_provider_for_project(
        self, project_id: str, requested_provider_id: str | None = None
    ) -> tuple[EmbeddingProvider, str]:
        """Resolve the embedding provider for a project.

        Priority: existing profile > requested > default.
        Raises ProviderMismatchError if requested provider conflicts with profile.
        Returns (provider_instance, provider_id).
        """
        profile = self.profile_repo.get_by_project(project_id)

        if profile is not None:
            if requested_provider_id and requested_provider_id != profile.provider_id:
                raise ProviderMismatchError(
                    f"项目已使用 {profile.provider_id}，切换到 {requested_provider_id} "
                    "需要刷新全部资料。"
                )
            provider = create_provider(profile.provider_id)
            return provider, profile.provider_id

        pid = requested_provider_id or get_default_provider_id()
        provider = create_provider(pid)
        return provider, pid

    # --- Private helpers ---

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise EmbeddingProjectNotFoundError

    def _get_active_source(self, source_id: str) -> KnowledgeSource:
        stmt = (
            select(KnowledgeSource)
            .where(KnowledgeSource.id == source_id)
            .where(KnowledgeSource.deleted_at.is_(None))
        )
        source = self.db.scalar(stmt)
        if source is None:
            raise EmbeddingSourceNotFoundError
        return source

    def _get_active_chunks(self, source_id: str) -> list[KnowledgeChunk]:
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.source_id == source_id)
            .where(KnowledgeChunk.deleted_at.is_(None))
            .order_by(KnowledgeChunk.chunk_index)
        )
        return list(self.db.scalars(stmt).all())

    def _get_active_chunk(self, chunk_id: str) -> KnowledgeChunk | None:
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.id == chunk_id)
            .where(KnowledgeChunk.deleted_at.is_(None))
        )
        return self.db.scalar(stmt)

    def _delete_project_embeddings(self, project_id: str) -> None:
        from sqlalchemy import delete

        stmt = delete(KnowledgeEmbedding).where(
            KnowledgeEmbedding.project_id == project_id
        )
        self.db.execute(stmt)
        self.db.commit()

    @staticmethod
    def _build_chunk_text(chunk: KnowledgeChunk, source: KnowledgeSource) -> str:
        """Build the text to embed from chunk and source data.

        Combines source title, chunk heading, and chunk content
        to provide richer context for embedding.
        """
        parts: list[str] = []
        if source.title:
            parts.append(source.title)
        if chunk.heading:
            parts.append(chunk.heading)
        if chunk.content:
            parts.append(chunk.content)
        return "\n".join(parts)
