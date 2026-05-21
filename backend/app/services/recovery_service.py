from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.recovery_draft import RecoveryDraft
from app.schemas.recovery import RecoveryDraftCreate
from app.services.chapter_service import calculate_word_count


class RecoveryDraftNotFoundError(Exception):
    pass


class RecoveryChapterNotFoundError(Exception):
    pass


class RecoveryService:
    def __init__(self, db: Session):
        self.db = db

    def list_chapter_drafts(self, chapter_id: str) -> list[RecoveryDraft]:
        chapter = self._get_chapter(chapter_id)
        return list(
            self.db.scalars(
                select(RecoveryDraft)
                .where(RecoveryDraft.chapter_id == chapter.id)
                .order_by(RecoveryDraft.updated_at.desc())
            ).all()
        )

    def create_or_update_draft(
        self,
        chapter_id: str,
        data: RecoveryDraftCreate,
    ) -> RecoveryDraft:
        chapter = self._get_chapter(chapter_id)
        existing = self.db.scalar(
            select(RecoveryDraft)
            .where(RecoveryDraft.chapter_id == chapter.id)
            .order_by(RecoveryDraft.updated_at.desc())
        )
        now = datetime.now(timezone.utc)
        if existing is None:
            draft = RecoveryDraft(
                id=str(uuid4()),
                project_id=chapter.project_id,
                chapter_id=chapter.id,
                content=data.content,
                saved_content_snapshot=data.saved_content_snapshot,
                word_count=calculate_word_count(data.content),
                created_at=now,
                updated_at=now,
            )
            self.db.add(draft)
        else:
            draft = existing
            draft.content = data.content
            draft.saved_content_snapshot = data.saved_content_snapshot
            draft.word_count = calculate_word_count(data.content)
            draft.updated_at = now

        self.db.commit()
        self.db.refresh(draft)
        return draft

    def recover_draft(self, draft_id: str) -> Chapter:
        draft = self._get_draft(draft_id)
        chapter = self._get_chapter(draft.chapter_id)
        chapter.content = draft.content
        chapter.word_count = draft.word_count
        chapter.updated_at = datetime.now(timezone.utc)
        chapter.version += 1
        self.db.delete(draft)
        self.db.commit()
        self.db.refresh(chapter)
        return chapter

    def delete_draft(self, draft_id: str) -> None:
        draft = self._get_draft(draft_id)
        self.db.delete(draft)
        self.db.commit()

    def _get_chapter(self, chapter_id: str) -> Chapter:
        chapter = self.db.get(Chapter, chapter_id)
        if chapter is None or chapter.deleted_at is not None:
            raise RecoveryChapterNotFoundError()
        return chapter

    def _get_draft(self, draft_id: str) -> RecoveryDraft:
        draft = self.db.get(RecoveryDraft, draft_id)
        if draft is None:
            raise RecoveryDraftNotFoundError()
        return draft
