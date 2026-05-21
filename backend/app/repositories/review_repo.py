from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult
from app.models.prohibited_term import ProhibitedTerm


class ReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_prohibited_terms(self) -> list[ProhibitedTerm]:
        return list(
            self.db.scalars(
                select(ProhibitedTerm).order_by(
                    ProhibitedTerm.enabled.desc(),
                    ProhibitedTerm.updated_at.desc(),
                    ProhibitedTerm.term.asc(),
                )
            ).all()
        )

    def list_enabled_terms(self) -> list[ProhibitedTerm]:
        return list(
            self.db.scalars(
                select(ProhibitedTerm)
                .where(ProhibitedTerm.enabled.is_(True))
                .order_by(ProhibitedTerm.term.asc())
            ).all()
        )

    def get_term(self, term_id: str) -> ProhibitedTerm | None:
        return self.db.get(ProhibitedTerm, term_id)

    def delete_results_for_chapters(self, project_id: str, chapter_ids: list[str]) -> None:
        if not chapter_ids:
            return
        self.db.execute(
            delete(CheckResult).where(
                CheckResult.project_id == project_id,
                CheckResult.chapter_id.in_(chapter_ids),
                CheckResult.rule_type == "prohibited_term",
            )
        )
