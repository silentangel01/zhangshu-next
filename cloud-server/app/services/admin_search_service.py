"""Admin search service — validates, queries, and sanitises results.

The service enforces:

- minimum keyword length (``admin_search_min_keyword_length``);
- maximum keyword length (100);
- maximum 10 results per entity type;
- email masking for users without ``users:sensitive_view``;
- feedback description is never returned — only title and status.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.search_repo import SearchRepository

logger = logging.getLogger(__name__)


MAX_KEYWORD_LENGTH = 100
MAX_RESULTS_PER_TYPE = 10


class AdminSearchError(Exception):
    """Raised when the search request is invalid."""


def mask_email(email: str) -> str:
    """Mask an email for non-sensitive-view users: j***@example.com."""
    parts = email.split("@")
    if len(parts) != 2:
        return email
    local, domain = parts
    if len(local) <= 1:
        masked_local = "***"
    else:
        masked_local = local[0] + "***"
    return f"{masked_local}@{domain}"


class AdminSearchService:
    def __init__(self, db: Session, *, can_view_sensitive: bool):
        self._repo = SearchRepository(db)
        self._can_view_sensitive = can_view_sensitive
        self._settings = get_settings()

    def search(self, q: str) -> dict[str, Any]:
        q = (q or "").strip()
        min_len = self._settings.admin_search_min_keyword_length
        if len(q) < min_len:
            raise AdminSearchError(
                f"搜索关键字至少需要 {min_len} 个字符。"
            )
        if len(q) > MAX_KEYWORD_LENGTH:
            raise AdminSearchError(
                f"搜索关键字最多 {MAX_KEYWORD_LENGTH} 个字符。"
            )

        users = self._repo.search_users(q, MAX_RESULTS_PER_TYPE)
        if not self._can_view_sensitive:
            for u in users:
                u["email"] = mask_email(u["email"])

        feedback = self._repo.search_feedback(q, MAX_RESULTS_PER_TYPE)
        announcements = self._repo.search_announcements(q, MAX_RESULTS_PER_TYPE)

        return {
            "users": users,
            "feedback": feedback,
            "announcements": announcements,
        }
