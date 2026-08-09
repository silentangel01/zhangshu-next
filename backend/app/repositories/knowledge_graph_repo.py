from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_graph_entity import KnowledgeGraphEntity
from app.models.knowledge_graph_evidence import KnowledgeGraphEvidence
from app.models.knowledge_graph_extraction_run import KnowledgeGraphExtractionRun
from app.models.knowledge_graph_relation import KnowledgeGraphRelation
from app.models.knowledge_source import KnowledgeSource


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class KnowledgeGraphChunkInput:
    chunk: KnowledgeChunk
    source_title: str


class KnowledgeGraphRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Extraction inputs ---

    def get_project_source(self, project_id: str, source_id: str) -> KnowledgeSource | None:
        statement = select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.project_id == project_id,
            KnowledgeSource.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def list_extraction_chunks(
        self,
        project_id: str,
        *,
        source_id: str | None = None,
    ) -> list[KnowledgeGraphChunkInput]:
        statement = (
            select(KnowledgeChunk, KnowledgeSource.title)
            .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
            .where(
                KnowledgeChunk.project_id == project_id,
                KnowledgeChunk.deleted_at.is_(None),
                KnowledgeSource.deleted_at.is_(None),
                KnowledgeSource.status == "active",
            )
            .order_by(
                KnowledgeSource.updated_at.desc(),
                KnowledgeSource.created_at.desc(),
                KnowledgeChunk.chunk_index.asc(),
            )
        )
        if source_id is not None:
            statement = statement.where(KnowledgeChunk.source_id == source_id)

        rows = self.db.execute(statement).all()
        return [
            KnowledgeGraphChunkInput(chunk=chunk, source_title=source_title or "")
            for chunk, source_title in rows
        ]

    # --- Runs ---

    def create_run(
        self,
        run: KnowledgeGraphExtractionRun,
    ) -> KnowledgeGraphExtractionRun:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: str) -> KnowledgeGraphExtractionRun | None:
        statement = select(KnowledgeGraphExtractionRun).where(
            KnowledgeGraphExtractionRun.id == run_id,
            KnowledgeGraphExtractionRun.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def fail_active_runs(self, project_id: str, message: str) -> int:
        runs = list(
            self.db.scalars(
                select(KnowledgeGraphExtractionRun).where(
                    KnowledgeGraphExtractionRun.project_id == project_id,
                    KnowledgeGraphExtractionRun.deleted_at.is_(None),
                    KnowledgeGraphExtractionRun.status.in_(("pending", "running")),
                )
            ).all()
        )
        now = utc_now()
        for run in runs:
            run.status = "failed"
            run.error_message = message
            run.completed_at = now
        if runs:
            self.db.commit()
        return len(runs)

    def list_runs(
        self,
        project_id: str,
        *,
        limit: int = 20,
    ) -> list[KnowledgeGraphExtractionRun]:
        statement = (
            select(KnowledgeGraphExtractionRun)
            .where(
                KnowledgeGraphExtractionRun.project_id == project_id,
                KnowledgeGraphExtractionRun.deleted_at.is_(None),
            )
            .order_by(KnowledgeGraphExtractionRun.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    # --- Entities ---

    def add_entity(self, entity: KnowledgeGraphEntity) -> KnowledgeGraphEntity:
        self.db.add(entity)
        self.db.flush()
        return entity

    def get_entity(self, entity_id: str) -> KnowledgeGraphEntity | None:
        statement = select(KnowledgeGraphEntity).where(
            KnowledgeGraphEntity.id == entity_id,
            KnowledgeGraphEntity.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def get_entities_by_ids(self, entity_ids: set[str]) -> dict[str, KnowledgeGraphEntity]:
        if not entity_ids:
            return {}
        statement = select(KnowledgeGraphEntity).where(
            KnowledgeGraphEntity.id.in_(entity_ids),
            KnowledgeGraphEntity.deleted_at.is_(None),
        )
        return {entity.id: entity for entity in self.db.scalars(statement).all()}

    def find_entity_by_name_type(
        self,
        project_id: str,
        canonical_name: str,
        entity_type: str,
    ) -> KnowledgeGraphEntity | None:
        statement = (
            select(KnowledgeGraphEntity)
            .where(
                KnowledgeGraphEntity.project_id == project_id,
                KnowledgeGraphEntity.deleted_at.is_(None),
                KnowledgeGraphEntity.status != "rejected",
                func.lower(KnowledgeGraphEntity.canonical_name)
                == canonical_name.lower(),
                KnowledgeGraphEntity.entity_type == entity_type,
            )
            .order_by(KnowledgeGraphEntity.status.asc(), KnowledgeGraphEntity.created_at.asc())
        )
        return self.db.scalar(statement)

    def list_entities(
        self,
        project_id: str,
        *,
        status: str | None = None,
        entity_type: str | None = None,
        keyword: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeGraphEntity]:
        statement = select(KnowledgeGraphEntity).where(
            KnowledgeGraphEntity.project_id == project_id,
            KnowledgeGraphEntity.deleted_at.is_(None),
        )
        if status:
            statement = statement.where(KnowledgeGraphEntity.status == status)
        if entity_type:
            statement = statement.where(KnowledgeGraphEntity.entity_type == entity_type)
        if keyword:
            pattern = f"%{keyword}%"
            statement = statement.where(
                or_(
                    KnowledgeGraphEntity.canonical_name.ilike(pattern),
                    KnowledgeGraphEntity.description.ilike(pattern),
                    KnowledgeGraphEntity.aliases_json.ilike(pattern),
                )
            )
        statement = statement.order_by(
            KnowledgeGraphEntity.status.asc(),
            KnowledgeGraphEntity.updated_at.desc(),
        ).limit(limit)
        return list(self.db.scalars(statement).all())

    # --- Relations ---

    def add_relation(
        self,
        relation: KnowledgeGraphRelation,
    ) -> KnowledgeGraphRelation:
        self.db.add(relation)
        self.db.flush()
        return relation

    def get_relation(self, relation_id: str) -> KnowledgeGraphRelation | None:
        statement = select(KnowledgeGraphRelation).where(
            KnowledgeGraphRelation.id == relation_id,
            KnowledgeGraphRelation.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def find_relation(
        self,
        project_id: str,
        subject_entity_id: str,
        object_entity_id: str,
        relation_type: str,
        predicate_text: str,
    ) -> KnowledgeGraphRelation | None:
        statement = (
            select(KnowledgeGraphRelation)
            .where(
                KnowledgeGraphRelation.project_id == project_id,
                KnowledgeGraphRelation.deleted_at.is_(None),
                KnowledgeGraphRelation.status != "rejected",
                KnowledgeGraphRelation.subject_entity_id == subject_entity_id,
                KnowledgeGraphRelation.object_entity_id == object_entity_id,
                KnowledgeGraphRelation.relation_type == relation_type,
                func.lower(KnowledgeGraphRelation.predicate_text)
                == predicate_text.lower(),
            )
            .order_by(
                KnowledgeGraphRelation.status.asc(),
                KnowledgeGraphRelation.created_at.asc(),
            )
        )
        return self.db.scalar(statement)

    def list_relations(
        self,
        project_id: str,
        *,
        status: str | None = None,
        entity_id: str | None = None,
        relation_type: str | None = None,
        source_id: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeGraphRelation]:
        statement = select(KnowledgeGraphRelation).where(
            KnowledgeGraphRelation.project_id == project_id,
            KnowledgeGraphRelation.deleted_at.is_(None),
        )
        if status:
            statement = statement.where(KnowledgeGraphRelation.status == status)
        if entity_id:
            statement = statement.where(
                or_(
                    KnowledgeGraphRelation.subject_entity_id == entity_id,
                    KnowledgeGraphRelation.object_entity_id == entity_id,
                )
            )
        if relation_type:
            statement = statement.where(KnowledgeGraphRelation.relation_type == relation_type)
        if source_id:
            evidence_relation_ids = select(KnowledgeGraphEvidence.relation_id).where(
                KnowledgeGraphEvidence.project_id == project_id,
                KnowledgeGraphEvidence.source_id == source_id,
                KnowledgeGraphEvidence.relation_id.is_not(None),
                KnowledgeGraphEvidence.deleted_at.is_(None),
            )
            statement = statement.where(KnowledgeGraphRelation.id.in_(evidence_relation_ids))

        statement = statement.order_by(
            KnowledgeGraphRelation.status.asc(),
            KnowledgeGraphRelation.updated_at.desc(),
        ).limit(limit)
        return list(self.db.scalars(statement).all())

    # --- Evidence ---

    def add_evidence(
        self,
        evidence: KnowledgeGraphEvidence,
    ) -> KnowledgeGraphEvidence:
        self.db.add(evidence)
        self.db.flush()
        return evidence

    def list_evidence_for_relations(
        self,
        relation_ids: set[str],
    ) -> dict[str, list[KnowledgeGraphEvidence]]:
        if not relation_ids:
            return {}
        statement = (
            select(KnowledgeGraphEvidence)
            .where(
                KnowledgeGraphEvidence.relation_id.in_(relation_ids),
                KnowledgeGraphEvidence.deleted_at.is_(None),
            )
            .order_by(KnowledgeGraphEvidence.created_at.asc())
        )
        grouped: dict[str, list[KnowledgeGraphEvidence]] = {}
        for evidence in self.db.scalars(statement).all():
            if evidence.relation_id is None:
                continue
            grouped.setdefault(evidence.relation_id, []).append(evidence)
        return grouped

    # --- Unit of work helpers ---

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, model: object) -> None:
        self.db.refresh(model)
