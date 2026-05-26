from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_link import KnowledgeLink
from app.models.knowledge_source import KnowledgeSource


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- KnowledgeSource ---

    def list_sources(
        self,
        project_id: str,
        *,
        keyword: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        credibility: str | None = None,
    ) -> list[KnowledgeSource]:
        statement = select(KnowledgeSource).where(
            KnowledgeSource.project_id == project_id,
            KnowledgeSource.deleted_at.is_(None),
        )

        if source_type is not None:
            statement = statement.where(KnowledgeSource.source_type == source_type)
        if status is not None:
            statement = statement.where(KnowledgeSource.status == status)
        if credibility is not None:
            statement = statement.where(KnowledgeSource.credibility == credibility)
        if keyword:
            pattern = f"%{keyword}%"
            statement = statement.where(
                or_(
                    KnowledgeSource.title.ilike(pattern),
                    KnowledgeSource.content.ilike(pattern),
                    KnowledgeSource.summary.ilike(pattern),
                    KnowledgeSource.tags.ilike(pattern),
                )
            )
        if tag:
            pattern = f"%{tag}%"
            statement = statement.where(KnowledgeSource.tags.ilike(pattern))

        statement = statement.order_by(
            KnowledgeSource.updated_at.desc(),
            KnowledgeSource.created_at.desc(),
        )
        return list(self.db.scalars(statement).all())

    def get_source(self, source_id: str) -> KnowledgeSource | None:
        statement = select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create_source(self, source: KnowledgeSource) -> KnowledgeSource:
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def update_source(
        self, source: KnowledgeSource, values: dict[str, object]
    ) -> KnowledgeSource:
        for field, value in values.items():
            setattr(source, field, value)
        source.updated_at = utc_now()
        source.version += 1
        self.db.commit()
        self.db.refresh(source)
        return source

    def soft_delete_source(self, source: KnowledgeSource) -> KnowledgeSource:
        now = utc_now()
        source.deleted_at = now
        source.updated_at = now
        source.version += 1
        self.db.commit()
        self.db.refresh(source)
        return source

    # --- KnowledgeChunk ---

    def list_chunks_by_source(self, source_id: str) -> list[KnowledgeChunk]:
        statement = (
            select(KnowledgeChunk)
            .where(
                KnowledgeChunk.source_id == source_id,
                KnowledgeChunk.deleted_at.is_(None),
            )
            .order_by(KnowledgeChunk.chunk_index.asc())
        )
        return list(self.db.scalars(statement).all())

    def get_chunk(self, chunk_id: str) -> KnowledgeChunk | None:
        statement = select(KnowledgeChunk).where(
            KnowledgeChunk.id == chunk_id,
            KnowledgeChunk.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create_chunk(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    def soft_delete_chunks_by_source(self, source_id: str) -> int:
        now = utc_now()
        chunks = list(
            self.db.scalars(
                select(KnowledgeChunk).where(
                    KnowledgeChunk.source_id == source_id,
                    KnowledgeChunk.deleted_at.is_(None),
                )
            ).all()
        )
        count = 0
        for chunk in chunks:
            chunk.deleted_at = now
            chunk.updated_at = now
            count += 1
        if count > 0:
            self.db.commit()
        return count

    # --- KnowledgeLink ---

    def list_links_by_source(self, source_id: str) -> list[KnowledgeLink]:
        statement = (
            select(KnowledgeLink)
            .where(
                KnowledgeLink.source_id == source_id,
                KnowledgeLink.deleted_at.is_(None),
            )
            .order_by(KnowledgeLink.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_link(self, link_id: str) -> KnowledgeLink | None:
        statement = select(KnowledgeLink).where(
            KnowledgeLink.id == link_id,
            KnowledgeLink.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create_link(self, link: KnowledgeLink) -> KnowledgeLink:
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def soft_delete_link(self, link: KnowledgeLink) -> KnowledgeLink:
        link.deleted_at = utc_now()
        self.db.commit()
        self.db.refresh(link)
        return link
