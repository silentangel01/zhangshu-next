from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.check_result import CheckResult
from app.models.prohibited_term import ProhibitedTerm
from app.models.project import Project
from app.models.volume import Volume
from app.repositories.review_repo import ReviewRepository
from app.schemas.review import (
    CheckResultRead,
    ProhibitedTermCreate,
    ProhibitedTermUpdate,
    ReviewCheckRequest,
    ReviewCheckResponse,
)


class ReviewNotFoundError(Exception):
    pass


class ReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ReviewRepository(db)

    def list_prohibited_terms(self) -> list[ProhibitedTerm]:
        return self.repo.list_prohibited_terms()

    def create_prohibited_term(self, data: ProhibitedTermCreate) -> ProhibitedTerm:
        term = ProhibitedTerm(
            id=str(uuid4()),
            term=data.term.strip(),
            severity=data.severity.strip() or "medium",
            suggestion=data.suggestion,
            enabled=data.enabled,
        )
        self.db.add(term)
        self.db.commit()
        self.db.refresh(term)
        return term

    def update_prohibited_term(self, term_id: str, data: ProhibitedTermUpdate) -> ProhibitedTerm:
        term = self.repo.get_term(term_id)
        if term is None:
            raise ReviewNotFoundError()

        if data.term is not None:
            term.term = data.term.strip()
        if data.severity is not None:
            term.severity = data.severity.strip() or "medium"
        if data.suggestion is not None:
            term.suggestion = data.suggestion
        if data.enabled is not None:
            term.enabled = data.enabled
        term.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(term)
        return term

    def delete_prohibited_term(self, term_id: str) -> None:
        term = self.repo.get_term(term_id)
        if term is None:
            raise ReviewNotFoundError()
        self.db.delete(term)
        self.db.commit()

    def run_check(self, project_id: str, data: ReviewCheckRequest) -> ReviewCheckResponse:
        self._ensure_project(project_id)
        chapters = self._resolve_chapters(project_id, data)
        terms = self.repo.list_enabled_terms()
        chapter_ids = [chapter.id for chapter in chapters]

        self.repo.delete_results_for_chapters(project_id, chapter_ids)
        created_results: list[CheckResult] = []
        for chapter in chapters:
            for term in terms:
                for start, end in self._find_matches(chapter.content, term.term):
                    result = CheckResult(
                        id=str(uuid4()),
                        project_id=project_id,
                        chapter_id=chapter.id,
                        rule_type="prohibited_term",
                        matched_text=chapter.content[start:end],
                        severity=term.severity,
                        position_start=start,
                        position_end=end,
                        suggestion=term.suggestion,
                    )
                    self.db.add(result)
                    created_results.append(result)

        self.db.commit()
        return ReviewCheckResponse(
            total=len(created_results),
            results=self._hydrate_results(created_results),
        )

    def list_results(self, project_id: str) -> ReviewCheckResponse:
        self._ensure_project(project_id)
        results = list(
            self.db.scalars(
                select(CheckResult)
                .where(CheckResult.project_id == project_id)
                .order_by(CheckResult.created_at.desc(), CheckResult.chapter_id.asc())
            ).all()
        )
        hydrated = self._hydrate_results(results)
        return ReviewCheckResponse(total=len(hydrated), results=hydrated)

    def _ensure_project(self, project_id: str) -> None:
        project = self.db.get(Project, project_id)
        if project is None or project.deleted_at is not None:
            raise ReviewNotFoundError()

    def _resolve_chapters(self, project_id: str, data: ReviewCheckRequest) -> list[Chapter]:
        query = select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.deleted_at.is_(None),
        )
        if data.scope == "chapter":
            query = query.where(Chapter.id == data.chapter_id)
        elif data.scope == "volume":
            volume = self.db.get(Volume, data.volume_id)
            if volume is None or volume.project_id != project_id or volume.deleted_at is not None:
                raise ReviewNotFoundError()
            query = query.where(Chapter.volume_id == data.volume_id)

        chapters = list(
            self.db.scalars(
                query.order_by(Chapter.volume_id.asc(), Chapter.order_index.asc(), Chapter.created_at.asc())
            ).all()
        )
        if data.scope == "chapter" and not chapters:
            raise ReviewNotFoundError()
        return chapters

    def _find_matches(self, content: str, term: str) -> list[tuple[int, int]]:
        if not term:
            return []

        matches: list[tuple[int, int]] = []
        content_key = content.casefold()
        term_key = term.casefold()
        start = 0
        while True:
            index = content_key.find(term_key, start)
            if index < 0:
                break
            end = index + len(term)
            matches.append((index, end))
            start = max(index + len(term), index + 1)
        return matches

    def _hydrate_results(self, results: list[CheckResult]) -> list[CheckResultRead]:
        if not results:
            return []

        chapter_ids = {result.chapter_id for result in results}
        chapters = {
            chapter.id: chapter
            for chapter in self.db.scalars(
                select(Chapter).where(Chapter.id.in_(chapter_ids))
            ).all()
        }
        volume_ids = {chapter.volume_id for chapter in chapters.values() if chapter.volume_id}
        volumes = {
            volume.id: volume
            for volume in self.db.scalars(
                select(Volume).where(Volume.id.in_(volume_ids))
            ).all()
        } if volume_ids else {}

        hydrated = []
        for result in results:
            chapter = chapters.get(result.chapter_id)
            volume = volumes.get(chapter.volume_id) if chapter and chapter.volume_id else None
            hydrated.append(
                CheckResultRead(
                    id=result.id,
                    project_id=result.project_id,
                    chapter_id=result.chapter_id,
                    chapter_title=chapter.title if chapter else None,
                    volume_title=volume.title if volume else None,
                    rule_type=result.rule_type,
                    matched_text=result.matched_text,
                    severity=result.severity,
                    position_start=result.position_start,
                    position_end=result.position_end,
                    suggestion=result.suggestion,
                    created_at=result.created_at,
                )
            )
        return hydrated
