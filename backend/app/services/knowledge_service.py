import re
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_link import KnowledgeLink
from app.models.knowledge_source import KnowledgeSource
from app.repositories.knowledge_repo import KnowledgeRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.knowledge import (
    KnowledgeLinkCreate,
    KnowledgeSourceCreate,
    KnowledgeSourceUpdate,
)


CHUNK_MIN_CHARS = 800
CHUNK_MAX_CHARS = 1200


# --- Exceptions ---


class KnowledgeProjectNotFoundError(Exception):
    pass


class KnowledgeSourceNotFoundError(Exception):
    pass


class KnowledgeChunkNotFoundError(Exception):
    pass


class KnowledgeLinkNotFoundError(Exception):
    pass


# --- Service ---


class KnowledgeService:
    def __init__(self, db: Session):
        self.repo = KnowledgeRepository(db)
        self.project_repo = ProjectRepository(db)

    # --- Source CRUD ---

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
        self._ensure_project_exists(project_id)
        return self.repo.list_sources(
            project_id,
            keyword=keyword,
            source_type=source_type,
            status=status,
            tag=tag,
            credibility=credibility,
        )

    def create_source(
        self, project_id: str, data: KnowledgeSourceCreate
    ) -> KnowledgeSource:
        self._ensure_project_exists(project_id)
        source = KnowledgeSource(
            id=str(uuid4()),
            project_id=project_id,
            title=data.title,
            source_type=data.source_type,
            source_uri=data.source_uri,
            author=data.author,
            summary=data.summary,
            content=data.content,
            tags=data.tags,
            status=data.status,
            credibility=data.credibility,
        )
        source = self.repo.create_source(source)
        self._rebuild_chunks_for_source(source)
        return source

    def get_source(self, source_id: str) -> KnowledgeSource:
        source = self.repo.get_source(source_id)
        if source is None:
            raise KnowledgeSourceNotFoundError
        return source

    def update_source(
        self, source_id: str, data: KnowledgeSourceUpdate
    ) -> KnowledgeSource:
        source = self.get_source(source_id)
        values = data.model_dump(exclude_unset=True)
        content_changed = "content" in values and values["content"] != source.content
        source = self.repo.update_source(source, values)
        if content_changed:
            self._rebuild_chunks_for_source(source)
        return source

    def delete_source(self, source_id: str) -> KnowledgeSource:
        source = self.get_source(source_id)
        return self.repo.soft_delete_source(source)

    # --- Chunk ---

    def list_chunks(self, source_id: str) -> list[KnowledgeChunk]:
        self.get_source(source_id)
        return self.repo.list_chunks_by_source(source_id)

    def rebuild_chunks(self, source_id: str) -> list[KnowledgeChunk]:
        source = self.get_source(source_id)
        return self._rebuild_chunks_for_source(source)

    # --- Link ---

    def list_links(self, source_id: str) -> list[KnowledgeLink]:
        self.get_source(source_id)
        return self.repo.list_links_by_source(source_id)

    def create_link(
        self, source_id: str, data: KnowledgeLinkCreate
    ) -> KnowledgeLink:
        source = self.get_source(source_id)
        if data.chunk_id is not None:
            chunk = self.repo.get_chunk(data.chunk_id)
            if chunk is None or chunk.source_id != source_id:
                raise KnowledgeChunkNotFoundError
        link = KnowledgeLink(
            id=str(uuid4()),
            project_id=source.project_id,
            source_id=source_id,
            chunk_id=data.chunk_id,
            target_type=data.target_type,
            target_id=data.target_id,
            relation_type=data.relation_type,
            note=data.note,
        )
        return self.repo.create_link(link)

    def delete_link(self, link_id: str) -> KnowledgeLink:
        link = self.repo.get_link(link_id)
        if link is None:
            raise KnowledgeLinkNotFoundError
        return self.repo.soft_delete_link(link)

    # --- Private helpers ---

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise KnowledgeProjectNotFoundError

    def _rebuild_chunks_for_source(self, source: KnowledgeSource) -> list[KnowledgeChunk]:
        self.repo.soft_delete_chunks_by_source(source.id)
        if not source.content.strip():
            return []

        raw_chunks = self._split_content(source.content)
        chunks: list[KnowledgeChunk] = []
        for index, (heading, text) in enumerate(raw_chunks):
            chunk = KnowledgeChunk(
                id=str(uuid4()),
                project_id=source.project_id,
                source_id=source.id,
                chunk_index=index,
                heading=heading,
                content=text.strip(),
                token_count=len(text.strip()),
                metadata_json="{}",
            )
            chunk = self.repo.create_chunk(chunk)
            chunks.append(chunk)
        return chunks

    @staticmethod
    def _split_content(content: str) -> list[tuple[str, str]]:
        """Split content into (heading, text) chunks.

        Strategy:
        1. Split by markdown-style headings (# ... ## ... etc.) or double blank lines.
        2. Merge small sections until they reach CHUNK_MIN_CHARS.
        3. Split large sections at CHUNK_MAX_CHARS boundaries.
        """
        sections = _split_into_sections(content)
        merged = _merge_small_sections(sections)
        result: list[tuple[str, str]] = []
        for heading, text in merged:
            if len(text) <= CHUNK_MAX_CHARS:
                result.append((heading, text))
            else:
                for part in _split_large_text(text):
                    result.append((heading, part))
        return result


def _split_into_sections(content: str) -> list[tuple[str, str]]:
    """Split content by headings or double blank lines."""
    lines = content.split("\n")
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            if current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    sections.append((current_heading, text))
            current_heading = heading_match.group(2).strip()
            current_lines = []
        elif line.strip() == "" and current_lines and current_lines[-1].strip() == "":
            text = "\n".join(current_lines).strip()
            if text:
                sections.append((current_heading, text))
            current_heading = ""
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        text = "\n".join(current_lines).strip()
        if text:
            sections.append((current_heading, text))

    if not sections and content.strip():
        sections.append(("", content.strip()))

    return sections


def _merge_small_sections(
    sections: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Merge consecutive small sections until they reach CHUNK_MIN_CHARS."""
    if not sections:
        return sections

    merged: list[tuple[str, str]] = []
    current_heading = sections[0][0]
    current_text = sections[0][1]

    for heading, text in sections[1:]:
        if len(current_text) + len(text) + 1 <= CHUNK_MAX_CHARS and (
            len(current_text) < CHUNK_MIN_CHARS or not heading
        ):
            current_text = current_text + "\n\n" + text
            if heading and not current_heading:
                current_heading = heading
        else:
            merged.append((current_heading, current_text))
            current_heading = heading
            current_text = text

    merged.append((current_heading, current_text))
    return merged


def _split_large_text(text: str) -> list[str]:
    """Split a large text block into pieces of at most CHUNK_MAX_CHARS."""
    parts: list[str] = []
    while len(text) > CHUNK_MAX_CHARS:
        split_pos = text.rfind("\n", 0, CHUNK_MAX_CHARS)
        if split_pos <= 0:
            split_pos = text.rfind("。", 0, CHUNK_MAX_CHARS)
        if split_pos <= 0:
            split_pos = text.rfind("！", 0, CHUNK_MAX_CHARS)
        if split_pos <= 0:
            split_pos = text.rfind("？", 0, CHUNK_MAX_CHARS)
        if split_pos <= 0:
            split_pos = CHUNK_MAX_CHARS
        parts.append(text[:split_pos].strip())
        text = text[split_pos:].strip()
    if text:
        parts.append(text)
    return parts
