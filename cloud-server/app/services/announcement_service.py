"""Announcement business logic."""

from __future__ import annotations

import re
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.announcement import Announcement
from app.models.user import utc_now
from app.repositories.announcement_repo import AnnouncementRepository
from app.schemas.announcement import (
    AdminAnnouncementListResponse,
    AdminAnnouncementResponse,
    AnnouncementCreateRequest,
    AnnouncementListResponse,
    AnnouncementResponse,
    AnnouncementUpdateRequest,
)


class AnnouncementError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


# Basic unsafe HTML tag detection — announcement body must be plain text
_UNSAFE_HTML_RE = re.compile(r"<\s*/?\s*(script|iframe|object|embed|form|link|style)", re.I)


def _validate_plain_text_body(body: str) -> None:
    """Reject bodies that contain unsafe HTML tags."""
    if _UNSAFE_HTML_RE.search(body):
        raise AnnouncementError("公告正文不允许包含 HTML 标签。")


class AnnouncementService:
    def __init__(self, db: Session):
        self._db = db
        self._repo = AnnouncementRepository(db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_active(
        self,
        platform: str | None = None,
        app_version: str | None = None,
    ) -> AnnouncementListResponse:
        items = self._repo.list_active(platform=platform, app_version=app_version)
        total = self._repo.count_active(platform=platform)
        return AnnouncementListResponse(
            items=[
                AnnouncementResponse(
                    id=a.id,
                    title=a.title,
                    body=a.body,
                    severity=a.severity,
                    published_at=a.published_at,
                    starts_at=a.starts_at,
                    ends_at=a.ends_at,
                )
                for a in items
            ],
            total=total,
        )

    # ------------------------------------------------------------------
    # Admin API
    # ------------------------------------------------------------------

    def create(
        self, req: AnnouncementCreateRequest, admin_user_id: str
    ) -> AdminAnnouncementResponse:
        _validate_plain_text_body(req.body)
        announcement = Announcement(
            id=str(uuid4()),
            title=req.title,
            body=req.body,
            severity=req.severity,
            status="draft",
            audience=req.audience,
            platform=req.platform,
            min_app_version=req.min_app_version,
            max_app_version=req.max_app_version,
            starts_at=req.starts_at,
            ends_at=req.ends_at,
            created_by_id=admin_user_id,
        )
        self._repo.create(announcement)
        return self._to_admin_response(announcement)

    def list_admin(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AdminAnnouncementListResponse:
        items = self._repo.list_admin(status=status, limit=limit, offset=offset)
        total = self._repo.count_admin(status=status)
        return AdminAnnouncementListResponse(
            items=[self._to_admin_response(a) for a in items],
            total=total,
        )

    def get_admin(self, announcement_id: str) -> AdminAnnouncementResponse:
        a = self._repo.get_by_id(announcement_id)
        if a is None:
            raise AnnouncementError("公告不存在。", status_code=404)
        return self._to_admin_response(a)

    def update(
        self, announcement_id: str, req: AnnouncementUpdateRequest
    ) -> AdminAnnouncementResponse:
        a = self._repo.get_by_id(announcement_id)
        if a is None:
            raise AnnouncementError("公告不存在。", status_code=404)
        if a.status == "archived":
            raise AnnouncementError("已归档的公告不能修改。")

        values = req.model_dump(exclude_unset=True)
        if "body" in values and values["body"] is not None:
            _validate_plain_text_body(values["body"])
        if not values:
            raise AnnouncementError("没有需要更新的字段。")

        self._repo.update(a, values)
        return self._to_admin_response(a)

    def publish(self, announcement_id: str) -> AdminAnnouncementResponse:
        a = self._repo.get_by_id(announcement_id)
        if a is None:
            raise AnnouncementError("公告不存在。", status_code=404)
        if a.status == "archived":
            raise AnnouncementError("已归档的公告不能发布。")
        if a.status == "published":
            raise AnnouncementError("公告已经发布。")

        self._repo.update(a, {"status": "published", "published_at": utc_now()})
        return self._to_admin_response(a)

    def archive(self, announcement_id: str) -> AdminAnnouncementResponse:
        a = self._repo.get_by_id(announcement_id)
        if a is None:
            raise AnnouncementError("公告不存在。", status_code=404)

        self._repo.update(a, {"status": "archived"})
        return self._to_admin_response(a)

    def delete(self, announcement_id: str) -> None:
        a = self._repo.get_by_id(announcement_id)
        if a is None:
            raise AnnouncementError("公告不存在。", status_code=404)
        self._repo.soft_delete(a)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_admin_response(a: Announcement) -> AdminAnnouncementResponse:
        return AdminAnnouncementResponse(
            id=a.id,
            title=a.title,
            body=a.body,
            severity=a.severity,
            status=a.status,
            audience=a.audience,
            platform=a.platform,
            min_app_version=a.min_app_version,
            max_app_version=a.max_app_version,
            created_by_id=a.created_by_id,
            created_at=a.created_at,
            updated_at=a.updated_at,
            published_at=a.published_at,
            starts_at=a.starts_at,
            ends_at=a.ends_at,
        )
