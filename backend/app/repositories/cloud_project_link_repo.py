from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cloud_project_link import CloudProjectLink


class CloudProjectLinkRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_project(
        self, project_id: str, cloud_user_id: str
    ) -> CloudProjectLink | None:
        return self.db.scalar(
            select(CloudProjectLink).where(
                CloudProjectLink.project_id == project_id,
                CloudProjectLink.cloud_user_id == cloud_user_id,
                CloudProjectLink.deleted_at.is_(None),
            )
        )

    def get(self, link_id: str) -> CloudProjectLink | None:
        return self.db.scalar(
            select(CloudProjectLink).where(
                CloudProjectLink.id == link_id,
                CloudProjectLink.deleted_at.is_(None),
            )
        )

    def create(
        self, link: CloudProjectLink, *, commit: bool = True
    ) -> CloudProjectLink:
        self.db.add(link)
        if commit:
            self.db.commit()
            self.db.refresh(link)
        return link

    def update(
        self,
        link: CloudProjectLink,
        values: dict,
        *,
        commit: bool = True,
    ) -> CloudProjectLink:
        for key, value in values.items():
            setattr(link, key, value)
        if commit:
            self.db.commit()
            self.db.refresh(link)
        return link

    def soft_delete(
        self, link: CloudProjectLink, *, commit: bool = True
    ) -> None:
        link.deleted_at = datetime.now(timezone.utc)
        if commit:
            self.db.commit()
