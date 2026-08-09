from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.infrastructure.llm_provider import LLMProvider
from app.models.knowledge_graph_entity import KnowledgeGraphEntity
from app.models.knowledge_graph_evidence import KnowledgeGraphEvidence
from app.models.knowledge_graph_extraction_run import KnowledgeGraphExtractionRun
from app.models.knowledge_graph_relation import KnowledgeGraphRelation
from app.repositories.knowledge_graph_repo import (
    KnowledgeGraphChunkInput,
    KnowledgeGraphRepository,
)
from app.repositories.project_repo import ProjectRepository
from app.schemas.knowledge_graph import KnowledgeGraphExtractionRunCreate


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


MAX_EXTRACTION_CHUNKS = 80
MAX_CHUNK_PROMPT_CHARS = 6000
MAX_BATCH_PROMPT_CHARS = 10000
EXTRACTION_BATCH_SIZE = 4
MAX_EVIDENCE_CHARS = 600
MAX_LLM_RESPONSE_TOKENS = 2800

ENTITY_TYPES = {
    "character",
    "setting",
    "location",
    "organization",
    "item",
    "event",
    "clue",
    "concept",
    "custom",
}
RELATION_TYPES = {
    "relationship",
    "conflict",
    "ally",
    "family",
    "belongs_to",
    "located_in",
    "controls",
    "causes",
    "reveals",
    "foreshadows",
    "setting_related",
    "timeline_related",
    "custom",
}
FACT_STATUSES = {
    "confirmed",
    "claimed",
    "rumor",
    "hypothesis",
    "dream",
    "plan",
    "deprecated",
}

ENTITY_TYPE_ALIASES = {
    "人物": "character",
    "角色": "character",
    "设定": "setting",
    "地点": "location",
    "场景": "location",
    "组织": "organization",
    "势力": "organization",
    "物品": "item",
    "道具": "item",
    "事件": "event",
    "线索": "clue",
    "概念": "concept",
}

RELATION_TYPE_ALIASES = {
    "关系": "relationship",
    "冲突": "conflict",
    "盟友": "ally",
    "家族": "family",
    "隶属": "belongs_to",
    "属于": "belongs_to",
    "位于": "located_in",
    "控制": "controls",
    "导致": "causes",
    "揭示": "reveals",
    "伏笔": "foreshadows",
    "设定": "setting_related",
    "时间线": "timeline_related",
}

FACT_STATUS_ALIASES = {
    "事实": "confirmed",
    "确认": "confirmed",
    "声称": "claimed",
    "传闻": "rumor",
    "推测": "hypothesis",
    "梦境": "dream",
    "计划": "plan",
    "废弃": "deprecated",
}

EXTRACTION_SYSTEM_PROMPT = """
你是章枢写作资料的知识图谱抽取器。
请从用户提供的资料片段中抽取明确、可追溯的实体关系候选。
只抽取资料中已经表达的事实、设定、线索或剧情关系；不要补全、推理或创作新设定。
忽略修辞、闲聊、纯情绪、假设性问题和没有稳定事实含义的句子。

请只输出 JSON 对象，不要输出 Markdown，不要解释：
{
  "items": [
    {
      "subject": "实体名",
      "subject_type": "character|setting|location|organization|item|event|clue|concept|custom",
      "predicate": "关系短语",
      "object": "实体名",
      "object_type": "character|setting|location|organization|item|event|clue|concept|custom",
      "relation_type": "relationship|conflict|ally|family|belongs_to|located_in|controls|causes|reveals|foreshadows|setting_related|timeline_related|custom",
      "fact_status": "confirmed|claimed|rumor|hypothesis|dream|plan|deprecated",
      "confidence": 0.0,
      "evidence": "能支持该关系的原文短句",
      "chunk_ref": "chunk_1"
    }
  ]
}
""".strip()


@dataclass(frozen=True)
class ExtractedGraphItem:
    subject: str
    subject_type: str
    predicate: str
    object: str
    object_type: str
    relation_type: str
    fact_status: str
    confidence: float
    evidence: str
    chunk_ref: str | None = None


class KnowledgeGraphExtractionProjectNotFoundError(Exception):
    pass


class KnowledgeGraphExtractionSourceNotFoundError(Exception):
    pass


class KnowledgeGraphExtractionPrivacyNotConfirmedError(Exception):
    pass


class KnowledgeGraphExtractionMissingSourceError(Exception):
    pass


class KnowledgeGraphExtractionChunkLimitError(Exception):
    def __init__(self, chunk_count: int, max_chunks: int):
        super().__init__(f"Too many chunks: {chunk_count} > {max_chunks}")
        self.chunk_count = chunk_count
        self.max_chunks = max_chunks


class KnowledgeGraphExtractionError(Exception):
    pass


class KnowledgeGraphExtractionService:
    def __init__(self, db: Session, llm_provider: LLMProvider):
        self.repo = KnowledgeGraphRepository(db)
        self.project_repo = ProjectRepository(db)
        self.llm = llm_provider

    def run_extraction(
        self,
        project_id: str,
        data: KnowledgeGraphExtractionRunCreate,
    ) -> KnowledgeGraphExtractionRun:
        run = self.create_pending_run(project_id, data)
        return self.process_run(run.id)

    def create_pending_run(
        self,
        project_id: str,
        data: KnowledgeGraphExtractionRunCreate,
    ) -> KnowledgeGraphExtractionRun:
        self._ensure_project_exists(project_id)
        if not data.privacy_confirmed:
            raise KnowledgeGraphExtractionPrivacyNotConfirmedError

        if data.scope == "source" and not data.source_id:
            raise KnowledgeGraphExtractionMissingSourceError

        source_id = data.source_id if data.scope == "source" else None
        if source_id and self.repo.get_project_source(project_id, source_id) is None:
            raise KnowledgeGraphExtractionSourceNotFoundError

        chunks = self.repo.list_extraction_chunks(project_id, source_id=source_id)
        max_chunks = min(data.max_chunks, MAX_EXTRACTION_CHUNKS)
        if len(chunks) > max_chunks:
            raise KnowledgeGraphExtractionChunkLimitError(len(chunks), max_chunks)

        self.repo.fail_active_runs(project_id, "已被新的知识图谱抽取任务替换。")
        run = KnowledgeGraphExtractionRun(
            id=str(uuid4()),
            project_id=project_id,
            scope=data.scope,
            source_id=source_id,
            status="pending",
            model_name=self.llm.model_name,
            total_chunks=len(chunks),
            processed_chunks=0,
        )
        return self.repo.create_run(run)

    def process_run(self, run_id: str) -> KnowledgeGraphExtractionRun:
        run = self.repo.get_run(run_id)
        if run is None:
            raise KnowledgeGraphExtractionError("Extraction run not found.")

        chunks = self.repo.list_extraction_chunks(
            run.project_id,
            source_id=run.source_id if run.scope == "source" else None,
        )
        run.status = "running"
        run.model_name = self.llm.model_name
        run.total_chunks = len(chunks)
        run.started_at = run.started_at or utc_now()
        run.error_message = ""
        self.repo.commit()
        self.repo.refresh(run)

        entity_ids: set[str] = set()
        relation_ids: set[str] = set()

        try:
            for batch in _batch_chunks(chunks):
                self.repo.refresh(run)
                if run.status not in ("pending", "running"):
                    return run
                extracted_items = self._extract_chunk_batch(batch)
                for item, chunk_input in extracted_items:
                    self._store_item(
                        run.project_id,
                        item,
                        chunk_input,
                        run.id,
                        entity_ids,
                        relation_ids,
                    )
                run.processed_chunks += len(batch)
                self.repo.commit()
                self.repo.refresh(run)

            run.status = "completed"
            run.candidate_entity_count = len(entity_ids)
            run.candidate_relation_count = len(relation_ids)
            run.completed_at = utc_now()
            self.repo.commit()
            self.repo.refresh(run)
            return run
        except Exception as exc:
            self.repo.rollback()
            run = self.repo.get_run(run_id)
            if run is None:
                raise KnowledgeGraphExtractionError(str(exc)) from exc
            run.status = "failed"
            run.error_message = str(exc)[:1000]
            run.completed_at = utc_now()
            self.repo.commit()
            self.repo.refresh(run)
            raise KnowledgeGraphExtractionError(str(exc)) from exc

    def mark_run_failed(self, run_id: str, message: str) -> None:
        run = self.repo.get_run(run_id)
        if run is None:
            return
        run.status = "failed"
        run.error_message = message[:1000]
        run.completed_at = utc_now()
        self.repo.commit()

    def _extract_chunk(self, chunk_input: KnowledgeGraphChunkInput) -> list[ExtractedGraphItem]:
        chunk = chunk_input.chunk
        content = chunk.content.strip()
        if not content:
            return []
        if len(content) > MAX_CHUNK_PROMPT_CHARS:
            content = content[:MAX_CHUNK_PROMPT_CHARS]

        user_prompt = (
            f"资料标题：{chunk_input.source_title}\n"
            f"片段标题：{chunk.heading or '无'}\n"
            f"片段序号：{chunk.chunk_index + 1}\n\n"
            f"资料片段：\n{content}"
        )
        response_text = self.llm.complete(
            EXTRACTION_SYSTEM_PROMPT,
            user_prompt,
            temperature=0.1,
            max_tokens=MAX_LLM_RESPONSE_TOKENS,
        )
        return self._parse_response(response_text, chunk.content)

    def _extract_chunk_batch(
        self,
        batch: list[KnowledgeGraphChunkInput],
    ) -> list[tuple[ExtractedGraphItem, KnowledgeGraphChunkInput]]:
        ref_map: dict[str, KnowledgeGraphChunkInput] = {}
        sections: list[str] = []
        for index, chunk_input in enumerate(batch, 1):
            chunk = chunk_input.chunk
            content = chunk.content.strip()
            if not content:
                continue
            if len(content) > MAX_CHUNK_PROMPT_CHARS:
                content = content[:MAX_CHUNK_PROMPT_CHARS]

            ref = f"chunk_{index}"
            ref_map[ref] = chunk_input
            sections.append(
                "\n".join(
                    [
                        f"[{ref}]",
                        f"资料标题：{chunk_input.source_title}",
                        f"片段标题：{chunk.heading or '无'}",
                        f"片段序号：{chunk.chunk_index + 1}",
                        "片段正文：",
                        content,
                        f"[/{ref}]",
                    ]
                )
            )

        if not sections:
            return []

        user_prompt = (
            "请从以下多个资料片段中抽取知识图谱候选。"
            "每条候选都必须填写最能支撑该关系的 chunk_ref。\n\n"
            + "\n\n".join(sections)
        )
        response_text = self.llm.complete(
            EXTRACTION_SYSTEM_PROMPT,
            user_prompt,
            temperature=0.1,
            max_tokens=MAX_LLM_RESPONSE_TOKENS,
        )
        combined_content = "\n\n".join(item.chunk.content for item in batch)
        items = self._parse_response(response_text, combined_content)

        result: list[tuple[ExtractedGraphItem, KnowledgeGraphChunkInput]] = []
        for item in items:
            result.append((item, _resolve_item_chunk(item, ref_map, batch)))
        return result

    def _parse_response(
        self,
        response_text: str,
        chunk_content: str,
    ) -> list[ExtractedGraphItem]:
        payload = _load_json_payload(response_text)
        if payload is None:
            return []

        if isinstance(payload, dict):
            raw_items = (
                payload.get("items")
                or payload.get("tuples")
                or payload.get("relations")
                or []
            )
        else:
            raw_items = payload

        if not isinstance(raw_items, list):
            return []

        items: list[ExtractedGraphItem] = []
        for raw_item in raw_items:
            item = _coerce_extracted_item(raw_item, chunk_content)
            if item is not None:
                items.append(item)
        return items

    def _store_item(
        self,
        project_id: str,
        item: ExtractedGraphItem,
        chunk_input: KnowledgeGraphChunkInput,
        extraction_run_id: str,
        entity_ids: set[str],
        relation_ids: set[str],
    ) -> None:
        subject = self._get_or_create_entity(
            project_id,
            item.subject,
            item.subject_type,
            item.confidence,
        )
        obj = self._get_or_create_entity(
            project_id,
            item.object,
            item.object_type,
            item.confidence,
        )
        entity_ids.update({subject.id, obj.id})

        relation = self.repo.find_relation(
            project_id,
            subject.id,
            obj.id,
            item.relation_type,
            item.predicate,
        )
        now = utc_now()
        if relation is None:
            relation = KnowledgeGraphRelation(
                id=str(uuid4()),
                project_id=project_id,
                subject_entity_id=subject.id,
                object_entity_id=obj.id,
                relation_type=item.relation_type,
                predicate_text=item.predicate,
                direction="directed",
                fact_status=item.fact_status,
                status="candidate",
                confidence=item.confidence,
                source_count=1,
            )
            relation = self.repo.add_relation(relation)
        else:
            relation.confidence = max(relation.confidence, item.confidence)
            relation.source_count += 1
            relation.updated_at = now
            relation.version += 1
        relation_ids.add(relation.id)

        evidence_text, char_start, char_end = _build_evidence(
            item.evidence,
            chunk_input.chunk.content,
            item.subject,
            item.object,
        )
        self.repo.add_evidence(
            KnowledgeGraphEvidence(
                id=str(uuid4()),
                project_id=project_id,
                relation_id=relation.id,
                source_id=chunk_input.chunk.source_id,
                source_title=chunk_input.source_title,
                chunk_id=chunk_input.chunk.id,
                chunk_heading=chunk_input.chunk.heading,
                evidence_text=evidence_text,
                char_start=char_start,
                char_end=char_end,
                extraction_run_id=extraction_run_id,
            )
        )

    def _get_or_create_entity(
        self,
        project_id: str,
        canonical_name: str,
        entity_type: str,
        confidence: float,
    ) -> KnowledgeGraphEntity:
        entity = self.repo.find_entity_by_name_type(project_id, canonical_name, entity_type)
        now = utc_now()
        if entity is not None:
            entity.confidence = max(entity.confidence, confidence)
            entity.source_count += 1
            entity.updated_at = now
            entity.version += 1
            return entity

        return self.repo.add_entity(
            KnowledgeGraphEntity(
                id=str(uuid4()),
                project_id=project_id,
                canonical_name=canonical_name,
                entity_type=entity_type,
                status="candidate",
                confidence=confidence,
                source_count=1,
            )
        )

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise KnowledgeGraphExtractionProjectNotFoundError


def _batch_chunks(
    chunks: list[KnowledgeGraphChunkInput],
) -> list[list[KnowledgeGraphChunkInput]]:
    batches: list[list[KnowledgeGraphChunkInput]] = []
    current: list[KnowledgeGraphChunkInput] = []
    current_chars = 0

    for chunk_input in chunks:
        chunk_chars = min(len(chunk_input.chunk.content), MAX_CHUNK_PROMPT_CHARS)
        would_exceed_count = len(current) >= EXTRACTION_BATCH_SIZE
        would_exceed_chars = current and current_chars + chunk_chars > MAX_BATCH_PROMPT_CHARS
        if would_exceed_count or would_exceed_chars:
            batches.append(current)
            current = []
            current_chars = 0
        current.append(chunk_input)
        current_chars += chunk_chars

    if current:
        batches.append(current)
    return batches


def _resolve_item_chunk(
    item: ExtractedGraphItem,
    ref_map: dict[str, KnowledgeGraphChunkInput],
    batch: list[KnowledgeGraphChunkInput],
) -> KnowledgeGraphChunkInput:
    if item.chunk_ref and item.chunk_ref in ref_map:
        return ref_map[item.chunk_ref]

    best_input = batch[0]
    best_score = -1
    for chunk_input in batch:
        content = chunk_input.chunk.content
        score = 0
        if item.evidence and item.evidence in content:
            score += 5
        if item.subject and item.subject in content:
            score += 2
        if item.object and item.object in content:
            score += 2
        if item.predicate and item.predicate in content:
            score += 1
        if score > best_score:
            best_score = score
            best_input = chunk_input
    return best_input


def _load_json_payload(text: str) -> Any | None:
    raw = text.strip()
    if not raw:
        return None

    candidates = [raw]
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        candidates.append(fenced.group(1).strip())

    object_start = raw.find("{")
    object_end = raw.rfind("}")
    if 0 <= object_start < object_end:
        candidates.append(raw[object_start : object_end + 1])

    list_start = raw.find("[")
    list_end = raw.rfind("]")
    if 0 <= list_start < list_end:
        candidates.append(raw[list_start : list_end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except (TypeError, ValueError):
            continue
    return None


def _coerce_extracted_item(
    raw_item: Any,
    chunk_content: str,
) -> ExtractedGraphItem | None:
    if isinstance(raw_item, (list, tuple)) and len(raw_item) >= 5:
        subject, subject_type, predicate, obj, object_type = raw_item[:5]
        raw_item = {
            "subject": subject,
            "subject_type": subject_type,
            "predicate": predicate,
            "object": obj,
            "object_type": object_type,
        }

    if not isinstance(raw_item, dict):
        return None

    subject = _clean_text(_pick(raw_item, "subject", "head", "source"))
    obj = _clean_text(_pick(raw_item, "object", "tail", "target"))
    predicate = _clean_text(
        _pick(raw_item, "predicate", "relation", "relation_text", "description")
    )
    if not subject or not obj or not predicate or subject == obj:
        return None

    subject_type = _normalize_choice(
        _pick(raw_item, "subject_type", "head_type", "source_type"),
        ENTITY_TYPES,
        ENTITY_TYPE_ALIASES,
        "custom",
    )
    object_type = _normalize_choice(
        _pick(raw_item, "object_type", "tail_type", "target_type"),
        ENTITY_TYPES,
        ENTITY_TYPE_ALIASES,
        "custom",
    )
    relation_type = _normalize_choice(
        _pick(raw_item, "relation_type", "predicate_type"),
        RELATION_TYPES,
        RELATION_TYPE_ALIASES,
        _infer_relation_type(predicate),
    )
    fact_status = _normalize_choice(
        _pick(raw_item, "fact_status", "status"),
        FACT_STATUSES,
        FACT_STATUS_ALIASES,
        "confirmed",
    )
    confidence = _normalize_confidence(raw_item.get("confidence"), 0.6)
    evidence = _clean_text(raw_item.get("evidence"))[:MAX_EVIDENCE_CHARS]
    chunk_ref = _clean_text(raw_item.get("chunk_ref")) or None
    if not evidence:
        evidence, _, _ = _build_evidence("", chunk_content, subject, obj)

    return ExtractedGraphItem(
        subject=subject[:255],
        subject_type=subject_type,
        predicate=predicate[:255],
        object=obj[:255],
        object_type=object_type,
        relation_type=relation_type,
        fact_status=fact_status,
        confidence=confidence,
        evidence=evidence[:MAX_EVIDENCE_CHARS],
        chunk_ref=chunk_ref,
    )


def _pick(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value is not None:
            return value
    return ""


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().strip("\"'")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_choice(
    value: Any,
    allowed: set[str],
    aliases: dict[str, str],
    default: str,
) -> str:
    text = _clean_text(value)
    if not text:
        return default
    lowered = text.lower()
    if lowered in allowed:
        return lowered
    if text in aliases:
        return aliases[text]
    return default


def _normalize_confidence(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


def _infer_relation_type(predicate: str) -> str:
    text = predicate.lower()
    if any(token in predicate for token in ("父", "母", "兄", "姐", "弟", "妹", "亲属", "家族")):
        return "family"
    if any(token in predicate for token in ("位于", "坐落", "来自", "所在地")):
        return "located_in"
    if any(token in predicate for token in ("隶属", "属于", "成员", "效忠")):
        return "belongs_to"
    if any(token in predicate for token in ("敌", "冲突", "反对", "争夺")):
        return "conflict"
    if any(token in predicate for token in ("盟友", "协助", "同盟", "合作")):
        return "ally"
    if any(token in predicate for token in ("导致", "造成", "引发")):
        return "causes"
    if any(token in predicate for token in ("揭示", "暴露", "证明")):
        return "reveals"
    if any(token in predicate for token in ("伏笔", "预示", "暗示")):
        return "foreshadows"
    if any(token in text for token in ("control", "controls")) or "控制" in predicate:
        return "controls"
    return "custom"


def _build_evidence(
    evidence: str,
    content: str,
    subject: str,
    obj: str,
) -> tuple[str, int | None, int | None]:
    cleaned = _clean_text(evidence)
    if cleaned:
        index = content.find(cleaned)
        if index >= 0:
            return cleaned[:MAX_EVIDENCE_CHARS], index, index + len(cleaned)
        return cleaned[:MAX_EVIDENCE_CHARS], None, None

    subject_index = content.find(subject)
    object_index = content.find(obj)
    anchors = [idx for idx in (subject_index, object_index) if idx >= 0]
    if not anchors:
        snippet = content.strip()[:MAX_EVIDENCE_CHARS]
        return snippet, 0 if snippet else None, len(snippet) if snippet else None

    start = max(0, min(anchors) - 120)
    end = min(len(content), max(anchors) + 180)
    snippet = content[start:end].strip()
    return snippet[:MAX_EVIDENCE_CHARS], start, min(end, start + len(snippet))
