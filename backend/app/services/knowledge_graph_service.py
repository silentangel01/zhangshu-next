from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.knowledge_graph_entity import KnowledgeGraphEntity
from app.models.knowledge_graph_relation import KnowledgeGraphRelation
from app.repositories.knowledge_graph_repo import KnowledgeGraphRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.knowledge_graph import (
    KnowledgeGraphEntityRead,
    KnowledgeGraphEvidenceRead,
    KnowledgeGraphRelationRead,
    KnowledgeGraphSubgraph,
    KnowledgeGraphSubgraphEdge,
    KnowledgeGraphSubgraphNode,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeGraphProjectNotFoundError(Exception):
    pass


class KnowledgeGraphEntityNotFoundError(Exception):
    pass


class KnowledgeGraphRelationNotFoundError(Exception):
    pass


class KnowledgeGraphService:
    def __init__(self, db: Session):
        self.repo = KnowledgeGraphRepository(db)
        self.project_repo = ProjectRepository(db)

    def list_runs(self, project_id: str, *, limit: int = 20):
        self._ensure_project_exists(project_id)
        return self.repo.list_runs(project_id, limit=limit)

    def list_entities(
        self,
        project_id: str,
        *,
        status: str | None = None,
        entity_type: str | None = None,
        keyword: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeGraphEntity]:
        self._ensure_project_exists(project_id)
        return self.repo.list_entities(
            project_id,
            status=status,
            entity_type=entity_type,
            keyword=keyword,
            limit=limit,
        )

    def list_relations(
        self,
        project_id: str,
        *,
        status: str | None = None,
        entity_id: str | None = None,
        relation_type: str | None = None,
        source_id: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeGraphRelationRead]:
        self._ensure_project_exists(project_id)
        relations = self.repo.list_relations(
            project_id,
            status=status,
            entity_id=entity_id,
            relation_type=relation_type,
            source_id=source_id,
            limit=limit,
        )
        return self._build_relation_reads(relations)

    def accept_entity(self, project_id: str, entity_id: str) -> KnowledgeGraphEntity:
        return self._set_entity_status(project_id, entity_id, "accepted")

    def reject_entity(self, project_id: str, entity_id: str) -> KnowledgeGraphEntity:
        return self._set_entity_status(project_id, entity_id, "rejected")

    def accept_relation(
        self,
        project_id: str,
        relation_id: str,
    ) -> KnowledgeGraphRelationRead:
        relation = self._get_project_relation(project_id, relation_id)
        now = utc_now()

        subject = self.repo.get_entity(relation.subject_entity_id)
        obj = self.repo.get_entity(relation.object_entity_id)
        if subject is None or obj is None:
            raise KnowledgeGraphRelationNotFoundError

        for entity in (subject, obj):
            if entity.status == "candidate":
                entity.status = "accepted"
                entity.updated_at = now
                entity.version += 1

        relation.status = "accepted"
        relation.updated_at = now
        relation.version += 1
        self.repo.commit()
        self.repo.refresh(relation)
        return self._build_relation_reads([relation])[0]

    def reject_relation(
        self,
        project_id: str,
        relation_id: str,
    ) -> KnowledgeGraphRelationRead:
        relation = self._get_project_relation(project_id, relation_id)
        relation.status = "rejected"
        relation.updated_at = utc_now()
        relation.version += 1
        self.repo.commit()
        self.repo.refresh(relation)
        return self._build_relation_reads([relation])[0]

    def get_subgraph(
        self,
        project_id: str,
        *,
        status: str = "accepted",
        entity_id: str | None = None,
        limit: int = 100,
    ) -> KnowledgeGraphSubgraph:
        self._ensure_project_exists(project_id)
        relations = self.repo.list_relations(
            project_id,
            status=status,
            entity_id=entity_id,
            limit=limit,
        )
        entity_ids = {
            entity_id
            for relation in relations
            for entity_id in (relation.subject_entity_id, relation.object_entity_id)
        }
        entities = self.repo.get_entities_by_ids(entity_ids)

        nodes = [
            KnowledgeGraphSubgraphNode(
                id=entity.id,
                label=entity.canonical_name,
                entity_type=entity.entity_type,
                status=entity.status,
                confidence=entity.confidence,
            )
            for entity in sorted(entities.values(), key=lambda item: item.canonical_name)
        ]
        edges = [
            KnowledgeGraphSubgraphEdge(
                id=relation.id,
                source=relation.subject_entity_id,
                target=relation.object_entity_id,
                label=relation.predicate_text,
                relation_type=relation.relation_type,
                fact_status=relation.fact_status,
                confidence=relation.confidence,
            )
            for relation in relations
            if relation.subject_entity_id in entities and relation.object_entity_id in entities
        ]
        return KnowledgeGraphSubgraph(nodes=nodes, edges=edges)

    def _set_entity_status(
        self,
        project_id: str,
        entity_id: str,
        status: str,
    ) -> KnowledgeGraphEntity:
        entity = self.repo.get_entity(entity_id)
        if entity is None or entity.project_id != project_id:
            raise KnowledgeGraphEntityNotFoundError
        entity.status = status
        entity.updated_at = utc_now()
        entity.version += 1
        self.repo.commit()
        self.repo.refresh(entity)
        return entity

    def _get_project_relation(
        self,
        project_id: str,
        relation_id: str,
    ) -> KnowledgeGraphRelation:
        relation = self.repo.get_relation(relation_id)
        if relation is None or relation.project_id != project_id:
            raise KnowledgeGraphRelationNotFoundError
        return relation

    def _build_relation_reads(
        self,
        relations: list[KnowledgeGraphRelation],
    ) -> list[KnowledgeGraphRelationRead]:
        entity_ids = {
            entity_id
            for relation in relations
            for entity_id in (relation.subject_entity_id, relation.object_entity_id)
        }
        entities = self.repo.get_entities_by_ids(entity_ids)
        evidence_by_relation = self.repo.list_evidence_for_relations(
            {relation.id for relation in relations}
        )

        items: list[KnowledgeGraphRelationRead] = []
        for relation in relations:
            subject = entities.get(relation.subject_entity_id)
            obj = entities.get(relation.object_entity_id)
            if subject is None or obj is None:
                continue
            items.append(
                KnowledgeGraphRelationRead(
                    id=relation.id,
                    project_id=relation.project_id,
                    subject_entity_id=relation.subject_entity_id,
                    object_entity_id=relation.object_entity_id,
                    relation_type=relation.relation_type,
                    predicate_text=relation.predicate_text,
                    direction=relation.direction,
                    fact_status=relation.fact_status,
                    status=relation.status,
                    confidence=relation.confidence,
                    note=relation.note,
                    source_count=relation.source_count,
                    created_at=relation.created_at,
                    updated_at=relation.updated_at,
                    deleted_at=relation.deleted_at,
                    version=relation.version,
                    subject=KnowledgeGraphEntityRead.model_validate(subject),
                    object=KnowledgeGraphEntityRead.model_validate(obj),
                    evidence=[
                        KnowledgeGraphEvidenceRead.model_validate(evidence)
                        for evidence in evidence_by_relation.get(relation.id, [])
                    ],
                )
            )
        return items

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise KnowledgeGraphProjectNotFoundError
