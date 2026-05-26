from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.outline_item import OutlineItem
from app.repositories.chapter_repo import ChapterRepository
from app.repositories.outline_repo import OutlineRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.volume_repo import VolumeRepository
from app.schemas.outline import OutlineItemCreate, OutlineItemUpdate, OutlineReorderItem


class OutlineNotFoundError(Exception):
    pass


class OutlineProjectNotFoundError(Exception):
    pass


class OutlineVolumeNotFoundError(Exception):
    pass


class OutlineChapterNotFoundError(Exception):
    pass


class OutlineParentNotFoundError(Exception):
    pass


class OutlineInvalidParentError(Exception):
    pass


class OutlineCircularParentError(Exception):
    pass


class OutlineCrossProjectError(Exception):
    pass


class OutlineService:
    def __init__(self, db: Session):
        self.db = db
        self.outline_repo = OutlineRepository(db)
        self.project_repo = ProjectRepository(db)
        self.volume_repo = VolumeRepository(db)
        self.chapter_repo = ChapterRepository(db)

    def list_project_outlines(
        self,
        project_id: str,
        *,
        volume_id: str | None = None,
        chapter_id: str | None = None,
        item_type: str | None = None,
        status: str | None = None,
    ) -> list[OutlineItem]:
        self._ensure_project_exists(project_id)
        return self.outline_repo.list_active_by_project(
            project_id,
            volume_id=volume_id,
            chapter_id=chapter_id,
            item_type=item_type,
            status=status,
        )

    def create_outline(self, project_id: str, data: OutlineItemCreate) -> OutlineItem:
        self._ensure_project_exists(project_id)
        self._validate_links(
            project_id=project_id,
            parent_id=data.parent_id,
            volume_id=data.volume_id,
            chapter_id=data.chapter_id,
        )

        outline = OutlineItem(
            id=str(uuid4()),
            project_id=project_id,
            parent_id=data.parent_id,
            volume_id=data.volume_id,
            chapter_id=data.chapter_id,
            title=data.title,
            content=data.content,
            item_type=data.item_type,
            status=data.status,
            order_index=data.order_index,
            importance=data.importance,
        )
        return self.outline_repo.create(outline)

    def get_outline(self, outline_id: str) -> OutlineItem:
        outline = self.outline_repo.get_active(outline_id)
        if outline is None:
            raise OutlineNotFoundError
        return outline

    def update_outline(self, outline_id: str, data: OutlineItemUpdate) -> OutlineItem:
        outline = self.get_outline(outline_id)
        values = data.model_dump(exclude_unset=True)

        if values.get("parent_id") == outline.id:
            raise OutlineInvalidParentError

        self._validate_links(
            project_id=outline.project_id,
            parent_id=values.get("parent_id") if "parent_id" in values else outline.parent_id,
            volume_id=values.get("volume_id") if "volume_id" in values else outline.volume_id,
            chapter_id=values.get("chapter_id") if "chapter_id" in values else outline.chapter_id,
        )

        return self.outline_repo.update(outline, values)

    def delete_outline(self, outline_id: str) -> OutlineItem:
        outline = self.get_outline(outline_id)
        return self.outline_repo.soft_delete(outline)

    def list_chapter_outlines(self, chapter_id: str) -> list[OutlineItem]:
        chapter = self.chapter_repo.get_active(chapter_id)
        if chapter is None:
            raise OutlineChapterNotFoundError

        all_project_outlines = self.outline_repo.list_active_by_project(chapter.project_id)
        base_ids = {outline.id for outline in all_project_outlines if outline.chapter_id == chapter_id}
        if not base_ids:
            return []

        included_ids = set(base_ids)
        changed = True
        while changed:
            changed = False
            for outline in all_project_outlines:
                if outline.parent_id in included_ids and outline.id not in included_ids:
                    included_ids.add(outline.id)
                    changed = True

        return sorted(
            [outline for outline in all_project_outlines if outline.id in included_ids],
            key=lambda item: (item.order_index, item.created_at),
        )

    def list_volume_outlines(self, volume_id: str) -> list[OutlineItem]:
        volume = self.volume_repo.get_active(volume_id)
        if volume is None:
            raise OutlineVolumeNotFoundError

        return self.outline_repo.list_active_by_project(volume.project_id, volume_id=volume_id)

    def reorder_outlines(
        self, project_id: str, items: list[OutlineReorderItem]
    ) -> int:
        self._ensure_project_exists(project_id)

        all_outlines = self.outline_repo.list_active_by_project(project_id)
        outline_map = {o.id: o for o in all_outlines}

        # Validate all items belong to the project.
        for item in items:
            if item.outline_id not in outline_map:
                raise OutlineNotFoundError
            if item.parent_id is not None and item.parent_id not in outline_map:
                raise OutlineParentNotFoundError

        # Build proposed parent map and check for cross-project parents.
        proposed_parents: dict[str, str | None] = {}
        for item in items:
            if item.parent_id is not None:
                parent = outline_map[item.parent_id]
                if parent.project_id != project_id:
                    raise OutlineCrossProjectError
            proposed_parents[item.outline_id] = item.parent_id

        # Check for self-reference.
        for item in items:
            if item.parent_id == item.outline_id:
                raise OutlineInvalidParentError

        # Check for cycles: for each moved node, walk up the proposed parent chain.
        for item in items:
            visited = {item.outline_id}
            current_parent = item.parent_id
            while current_parent is not None:
                if current_parent in visited:
                    raise OutlineCircularParentError
                visited.add(current_parent)
                # Use proposed parent if this parent was also moved, else existing.
                current_parent = proposed_parents.get(
                    current_parent,
                    outline_map[current_parent].parent_id,
                )

        # Apply updates in a single transaction.
        return self.outline_repo.batch_reorder(items)

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise OutlineProjectNotFoundError

    def _validate_links(
        self,
        *,
        project_id: str,
        parent_id: str | None,
        volume_id: str | None,
        chapter_id: str | None,
    ) -> None:
        if parent_id is not None:
            parent = self.outline_repo.get_active(parent_id)
            if parent is None or parent.project_id != project_id:
                raise OutlineParentNotFoundError

        if volume_id is not None:
            volume = self.volume_repo.get_active(volume_id)
            if volume is None or volume.project_id != project_id:
                raise OutlineVolumeNotFoundError

        if chapter_id is not None:
            chapter = self.chapter_repo.get_active(chapter_id)
            if chapter is None or chapter.project_id != project_id:
                raise OutlineChapterNotFoundError
