"""Knowledge index refresh service — orchestrates chunk rebuild + embedding refresh."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.embedding_provider import EmbeddingProvider
from app.infrastructure.embedding_provider_factory import (
    create_provider,
    get_default_provider_id,
    get_provider_descriptor,
)
from app.models.knowledge_source import KnowledgeSource
from app.repositories.knowledge_index_profile_repo import KnowledgeIndexProfileRepository
from app.repositories.project_repo import ProjectRepository
from app.services.knowledge_embedding_service import (
    EmbeddingSourceNotFoundError,
    KnowledgeEmbeddingService,
    ProviderMismatchError,
)
from app.services.knowledge_service import (
    DEFAULT_CHUNK_SIZE,
    KnowledgeChunkSize,
    KnowledgeProjectNotFoundError,
    KnowledgeService,
)

KnowledgeIndexRefreshScope = Literal["project", "source"]


# --- Exceptions ---


class KnowledgeIndexRefreshProjectNotFoundError(Exception):
    pass


class KnowledgeIndexRefreshSourceNotFoundError(Exception):
    pass


class KnowledgeIndexRefreshInvalidScopeError(Exception):
    pass


class KnowledgeIndexPrivacyRequiredError(Exception):
    """Cloud provider used without privacy_confirmed=True."""


class KnowledgeIndexProviderUnavailableError(Exception):
    """Requested provider is not available."""


class KnowledgeIndexProviderConflictError(Exception):
    """Source-scope refresh uses different provider than project profile."""


# --- Result type ---


@dataclass
class KnowledgeIndexRefreshResult:
    source_count: int
    chunk_count: int
    indexed_count: int
    chunk_size: KnowledgeChunkSize
    model_name: str
    provider_id: str = ""
    profile_status: str = ""
    warnings: list[str] = field(default_factory=list)


# --- Service ---


class KnowledgeIndexRefreshService:
    """Orchestrates knowledge index refresh: rebuild chunks then refresh embeddings."""

    def __init__(self, db: Session):
        self.db = db
        self.knowledge_service = KnowledgeService(db)
        self.embedding_service = KnowledgeEmbeddingService(db)
        self.project_repo = ProjectRepository(db)
        self.profile_repo = KnowledgeIndexProfileRepository(db)

    def refresh_project(
        self,
        project_id: str,
        chunk_size: KnowledgeChunkSize = DEFAULT_CHUNK_SIZE,
        provider_id: str | None = None,
        privacy_confirmed: bool = False,
    ) -> KnowledgeIndexRefreshResult:
        """Refresh index for all active sources in a project."""
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise KnowledgeIndexRefreshProjectNotFoundError

        # Resolve and validate provider
        resolved_provider, resolved_pid = self._resolve_and_validate_provider(
            project_id, provider_id, privacy_confirmed
        )
        descriptor = get_provider_descriptor(resolved_pid)

        # Re-create embedding service with resolved provider
        self.embedding_service = KnowledgeEmbeddingService(
            self.db, provider=resolved_provider, store=self.embedding_service.store
        )

        # Get all active sources
        sources = self._get_active_sources(project_id)
        if not sources:
            # Still write profile even with no sources so the provider is recorded
            now = datetime.now(timezone.utc)
            self.profile_repo.upsert(
                project_id=project_id,
                provider_id=resolved_pid,
                provider_type=descriptor.provider_type,
                display_name=descriptor.display_name,
                model_name=resolved_provider.model_name,
                vector_dim=resolved_provider.vector_dim,
                chunk_size=chunk_size,
                status="ready",
                last_refreshed_at=now,
                last_error=None,
            )
            return KnowledgeIndexRefreshResult(
                source_count=0,
                chunk_count=0,
                indexed_count=0,
                chunk_size=chunk_size,
                model_name=resolved_provider.model_name,
                provider_id=resolved_pid,
                profile_status="ready",
                warnings=["该项目下暂无活跃资料。"],
            )

        warnings: list[str] = []
        total_chunks = 0
        empty_sources: list[str] = []

        # Rebuild chunks for each source
        for source in sources:
            if not source.content.strip():
                empty_sources.append(source.title)
                continue
            chunks = self.knowledge_service.rebuild_chunks(source.id, chunk_size=chunk_size)
            total_chunks += len(chunks)

        if empty_sources:
            warnings.append(
                f"以下资料内容为空，未生成索引片段：{'、'.join(empty_sources[:5])}"
                + ("…" if len(empty_sources) > 5 else "")
            )

        # Delete old project embeddings and rebuild
        self.embedding_service._delete_project_embeddings(project_id)

        try:
            indexed_count = self.embedding_service.rebuild_project_index(project_id)
        except Exception as exc:
            # Record error in profile on cloud failure
            self.profile_repo.mark_error(
                project_id, f"{type(exc).__name__}: {str(exc)[:200]}"
            )
            raise

        # Update profile AFTER successful rebuild
        now = datetime.now(timezone.utc)
        self.profile_repo.upsert(
            project_id=project_id,
            provider_id=resolved_pid,
            provider_type=descriptor.provider_type,
            display_name=descriptor.display_name,
            model_name=resolved_provider.model_name,
            vector_dim=resolved_provider.vector_dim,
            chunk_size=chunk_size,
            status="ready",
            last_refreshed_at=now,
            last_error=None,
        )

        return KnowledgeIndexRefreshResult(
            source_count=len(sources),
            chunk_count=total_chunks,
            indexed_count=indexed_count,
            chunk_size=chunk_size,
            model_name=resolved_provider.model_name,
            provider_id=resolved_pid,
            profile_status="ready",
            warnings=warnings,
        )

    def refresh_source(
        self,
        source_id: str,
        chunk_size: KnowledgeChunkSize = DEFAULT_CHUNK_SIZE,
        provider_id: str | None = None,
        privacy_confirmed: bool = False,
    ) -> KnowledgeIndexRefreshResult:
        """Refresh index for a single source."""
        try:
            source = self.knowledge_service.get_source(source_id)
        except Exception:
            raise KnowledgeIndexRefreshSourceNotFoundError

        project_id = source.project_id

        # Check provider consistency for source-scope refresh
        profile = self.profile_repo.get_by_project(project_id)
        if profile and provider_id and provider_id != profile.provider_id:
            raise KnowledgeIndexProviderConflictError(
                f"资料级刷新不能切换模型。项目当前使用 {profile.provider_id}，"
                f"请使用「全部资料」范围刷新来切换到 {provider_id}。"
            )

        # Use existing profile provider if no provider_id specified
        effective_pid = provider_id or (profile.provider_id if profile else None)
        resolved_provider, resolved_pid = self._resolve_and_validate_provider(
            project_id, effective_pid, privacy_confirmed
        )
        descriptor = get_provider_descriptor(resolved_pid)

        # Re-create embedding service with resolved provider
        self.embedding_service = KnowledgeEmbeddingService(
            self.db, provider=resolved_provider, store=self.embedding_service.store
        )

        warnings: list[str] = []
        total_chunks = 0

        if not source.content.strip():
            warnings.append(f"资料「{source.title}」内容为空，未生成索引片段。")
        else:
            chunks = self.knowledge_service.rebuild_chunks(source_id, chunk_size=chunk_size)
            total_chunks = len(chunks)

        # Remove old embeddings for this source, then re-index
        self.embedding_service.remove_source_embeddings(source_id)
        indexed_count = 0
        if total_chunks > 0:
            indexed_count = self.embedding_service.index_source(source_id)

        # If no profile exists, create one from source-scope refresh
        if profile is None:
            now = datetime.now(timezone.utc)
            self.profile_repo.upsert(
                project_id=project_id,
                provider_id=resolved_pid,
                provider_type=descriptor.provider_type,
                display_name=descriptor.display_name,
                model_name=resolved_provider.model_name,
                vector_dim=resolved_provider.vector_dim,
                chunk_size=chunk_size,
                status="ready",
                last_refreshed_at=now,
                last_error=None,
            )

        return KnowledgeIndexRefreshResult(
            source_count=1,
            chunk_count=total_chunks,
            indexed_count=indexed_count,
            chunk_size=chunk_size,
            model_name=resolved_provider.model_name,
            provider_id=resolved_pid,
            profile_status="ready" if profile is None else (profile.status or "ready"),
            warnings=warnings,
        )

    # --- Private helpers ---

    def _resolve_and_validate_provider(
        self,
        project_id: str,
        requested_provider_id: str | None,
        privacy_confirmed: bool,
    ) -> tuple[EmbeddingProvider, str]:
        """Resolve and validate provider for a refresh operation.

        Checks availability and privacy requirements.
        Returns (provider_instance, provider_id).
        """
        pid = requested_provider_id or get_default_provider_id()
        descriptor = get_provider_descriptor(pid)

        if not descriptor.available:
            raise KnowledgeIndexProviderUnavailableError(
                f"Provider '{pid}' 不可用：{descriptor.reason}"
            )

        if descriptor.requires_privacy_confirm and not privacy_confirmed:
            raise KnowledgeIndexPrivacyRequiredError(
                "使用云端 Embedding 服务需要确认隐私条款。"
            )

        provider = create_provider(pid)
        return provider, pid

    def _get_active_sources(self, project_id: str) -> list[KnowledgeSource]:
        stmt = (
            select(KnowledgeSource)
            .where(KnowledgeSource.project_id == project_id)
            .where(KnowledgeSource.deleted_at.is_(None))
        )
        return list(self.db.scalars(stmt).all())
