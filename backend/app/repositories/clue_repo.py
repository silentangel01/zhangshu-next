from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.clue import Clue


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ClueRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_project(
        self,
        project_id: str,
        *,
        status: str | None = None,
        visibility: str | None = None,
        importance: str | None = None,
        keyword: str | None = None,
    ) -> list[Clue]:
        statement = select(Clue).where(
            Clue.project_id == project_id,
            Clue.deleted_at.is_(None),
        )
        if status is not None:
            statement = statement.where(Clue.status == status)
        if visibility is not None:
            statement = statement.where(Clue.visibility == visibility)
        if importance is not None:
            statement = statement.where(Clue.importance == importance)
        if keyword:
            pattern = f"%{keyword}%"
            statement = statement.where(
                or_(
                    Clue.title.ilike(pattern),
                    Clue.description.ilike(pattern),
                    Clue.payoff_plan.ilike(pattern),
                    Clue.actual_payoff.ilike(pattern),
                    Clue.note.ilike(pattern),
                )
            )
        statement = statement.order_by(Clue.updated_at.desc(), Clue.created_at.desc())
        return list(self.db.scalars(statement).all())

    def get_active(self, clue_id: str) -> Clue | None:
        statement = select(Clue).where(Clue.id == clue_id, Clue.deleted_at.is_(None))
        return self.db.scalar(statement)

    def create(self, clue: Clue) -> Clue:
        self.db.add(clue)
        self.db.commit()
        self.db.refresh(clue)
        return clue

    def update(self, clue: Clue, values: dict[str, object]) -> Clue:
        for field, value in values.items():
            setattr(clue, field, value)
        clue.updated_at = utc_now()
        clue.version += 1
        self.db.commit()
        self.db.refresh(clue)
        return clue

    def soft_delete(self, clue: Clue) -> Clue:
        now = utc_now()
        clue.deleted_at = now
        clue.updated_at = now
        clue.version += 1
        self.db.commit()
        self.db.refresh(clue)
        return clue
