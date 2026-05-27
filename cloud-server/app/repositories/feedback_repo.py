"""Feedback ticket and attachment data access layer."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.feedback_attachment import FeedbackAttachment
from app.models.feedback_reply import FeedbackReply
from app.models.feedback_ticket import FeedbackTicket
from app.models.user import utc_now


class FeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Tickets
    # ------------------------------------------------------------------

    def create_ticket(
        self, ticket: FeedbackTicket, *, commit: bool = True
    ) -> FeedbackTicket:
        self.db.add(ticket)
        if commit:
            self.db.commit()
            self.db.refresh(ticket)
        return ticket

    def get_ticket(self, ticket_id: str) -> FeedbackTicket | None:
        return self.db.scalar(
            select(FeedbackTicket).where(
                FeedbackTicket.id == ticket_id,
                FeedbackTicket.deleted_at.is_(None),
            )
        )

    def list_tickets(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FeedbackTicket]:
        stmt = select(FeedbackTicket).where(FeedbackTicket.deleted_at.is_(None))
        if status:
            stmt = stmt.where(FeedbackTicket.status == status)
        if category:
            stmt = stmt.where(FeedbackTicket.category == category)
        if user_id:
            stmt = stmt.where(FeedbackTicket.user_id == user_id)
        stmt = stmt.order_by(FeedbackTicket.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_tickets(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
    ) -> int:
        subq = select(FeedbackTicket).where(FeedbackTicket.deleted_at.is_(None))
        if status:
            subq = subq.where(FeedbackTicket.status == status)
        if category:
            subq = subq.where(FeedbackTicket.category == category)
        if user_id:
            subq = subq.where(FeedbackTicket.user_id == user_id)
        stmt = select(func.count()).select_from(subq.subquery())
        return self.db.scalar(stmt) or 0

    def update_ticket(
        self,
        ticket: FeedbackTicket,
        values: dict,
        *,
        commit: bool = True,
    ) -> FeedbackTicket:
        for key, value in values.items():
            setattr(ticket, key, value)
        ticket.updated_at = utc_now()
        if commit:
            self.db.commit()
            self.db.refresh(ticket)
        return ticket

    def soft_delete_ticket(
        self, ticket: FeedbackTicket, *, commit: bool = True
    ) -> None:
        ticket.deleted_at = utc_now()
        if commit:
            self.db.commit()

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    def create_attachment(
        self, attachment: FeedbackAttachment, *, commit: bool = True
    ) -> FeedbackAttachment:
        self.db.add(attachment)
        if commit:
            self.db.commit()
            self.db.refresh(attachment)
        return attachment

    def create_attachments_batch(
        self, attachments: list[FeedbackAttachment], *, commit: bool = True
    ) -> list[FeedbackAttachment]:
        self.db.add_all(attachments)
        if commit:
            self.db.commit()
            for att in attachments:
                self.db.refresh(att)
        return attachments

    def get_attachment(self, attachment_id: str) -> FeedbackAttachment | None:
        return self.db.scalar(
            select(FeedbackAttachment).where(
                FeedbackAttachment.id == attachment_id,
                FeedbackAttachment.deleted_at.is_(None),
            )
        )

    def get_attachment_by_upload_id(self, upload_id: str) -> FeedbackAttachment | None:
        return self.db.scalar(
            select(FeedbackAttachment).where(
                FeedbackAttachment.upload_id == upload_id,
                FeedbackAttachment.deleted_at.is_(None),
            )
        )

    def list_attachments(self, feedback_id: str) -> list[FeedbackAttachment]:
        stmt = (
            select(FeedbackAttachment)
            .where(
                FeedbackAttachment.feedback_id == feedback_id,
                FeedbackAttachment.deleted_at.is_(None),
            )
            .order_by(FeedbackAttachment.created_at)
        )
        return list(self.db.scalars(stmt).all())

    def mark_uploaded(
        self, attachment: FeedbackAttachment, *, commit: bool = True
    ) -> FeedbackAttachment:
        attachment.status = "uploaded"
        attachment.uploaded_at = utc_now()
        if commit:
            self.db.commit()
            self.db.refresh(attachment)
        return attachment

    def mark_failed(
        self, attachment: FeedbackAttachment, *, commit: bool = True
    ) -> FeedbackAttachment:
        attachment.status = "failed"
        if commit:
            self.db.commit()
            self.db.refresh(attachment)
        return attachment

    def soft_delete_attachment(
        self, attachment: FeedbackAttachment, *, commit: bool = True
    ) -> None:
        attachment.deleted_at = utc_now()
        attachment.status = "deleted"
        if commit:
            self.db.commit()

    def anonymize_user_feedback(
        self, user_id: str, *, commit: bool = True
    ) -> int:
        """Remove user association and contact info from feedback tickets.

        Returns the count of affected tickets.
        """
        stmt = select(FeedbackTicket).where(
            FeedbackTicket.user_id == user_id,
            FeedbackTicket.deleted_at.is_(None),
        )
        tickets = list(self.db.scalars(stmt).all())
        for ticket in tickets:
            ticket.user_id = None
            ticket.contact_email = None
            ticket.updated_at = utc_now()
        if commit and tickets:
            self.db.commit()
        return len(tickets)

    def list_user_attachments(self, user_id: str) -> list[FeedbackAttachment]:
        """Return all attachments for feedback tickets owned by a user."""
        stmt = (
            select(FeedbackAttachment)
            .join(FeedbackTicket, FeedbackAttachment.feedback_id == FeedbackTicket.id)
            .where(
                FeedbackTicket.user_id == user_id,
                FeedbackAttachment.deleted_at.is_(None),
                FeedbackAttachment.status == "uploaded",
            )
        )
        return list(self.db.scalars(stmt).all())

    # ------------------------------------------------------------------
    # Replies
    # ------------------------------------------------------------------

    def create_reply(
        self, reply: FeedbackReply, *, commit: bool = True
    ) -> FeedbackReply:
        self.db.add(reply)
        if commit:
            self.db.commit()
            self.db.refresh(reply)
        return reply

    def list_replies(self, ticket_id: str) -> list[FeedbackReply]:
        stmt = (
            select(FeedbackReply)
            .where(
                FeedbackReply.ticket_id == ticket_id,
                FeedbackReply.deleted_at.is_(None),
            )
            .order_by(FeedbackReply.created_at)
        )
        return list(self.db.scalars(stmt).all())

    def count_replies(self, ticket_id: str) -> int:
        subq = select(FeedbackReply).where(
            FeedbackReply.ticket_id == ticket_id,
            FeedbackReply.deleted_at.is_(None),
        )
        stmt = select(func.count()).select_from(subq.subquery())
        return self.db.scalar(stmt) or 0

    def count_replies_batch(self, ticket_ids: list[str]) -> dict[str, int]:
        """Batch count replies for multiple tickets (avoids N+1)."""
        if not ticket_ids:
            return {}
        stmt = (
            select(
                FeedbackReply.ticket_id,
                func.count(FeedbackReply.id),
            )
            .where(
                FeedbackReply.ticket_id.in_(ticket_ids),
                FeedbackReply.deleted_at.is_(None),
            )
            .group_by(FeedbackReply.ticket_id)
        )
        return dict(self.db.execute(stmt).all())

    def get_reply(self, reply_id: str) -> FeedbackReply | None:
        return self.db.scalar(
            select(FeedbackReply).where(
                FeedbackReply.id == reply_id,
                FeedbackReply.deleted_at.is_(None),
            )
        )

    def soft_delete_reply(
        self, reply: FeedbackReply, *, commit: bool = True
    ) -> None:
        reply.deleted_at = utc_now()
        if commit:
            self.db.commit()
