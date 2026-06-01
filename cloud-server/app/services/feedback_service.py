"""Feedback business logic — creation, upload coordination, admin management."""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.infrastructure.oss_storage import OSSStorage, OSSError
from app.models.feedback_attachment import FeedbackAttachment, utc_now
from app.models.feedback_reply import FeedbackReply
from app.models.feedback_ticket import FeedbackTicket
from app.models.user import User
from app.repositories.feedback_repo import FeedbackRepository
from app.schemas.feedback import (
    AdminDownloadUrlResponse,
    AdminFeedbackListResponse,
    AdminFeedbackReplyCreateRequest,
    AdminFeedbackReplyListResponse,
    AdminFeedbackResponse,
    AdminFeedbackAttachmentResponse,
    AdminFeedbackUpdateRequest,
    ClientFeedbackItem,
    ClientFeedbackListResponse,
    FeedbackCompleteRequest,
    FeedbackCompleteResponse,
    FeedbackCreateRequest,
    FeedbackCreateResponse,
    FeedbackReplyResponse,
    UploadSlot,
)
from app.services.rate_limit_service import RateLimitError, RateLimitService

logger = logging.getLogger(__name__)

# Valid categories and statuses
VALID_CATEGORIES = {"bug", "suggestion", "data_loss", "cloud", "ui", "other"}
VALID_STATUSES = {"open", "triaged", "in_progress", "closed", "spam"}
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}


class FeedbackError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class FeedbackService:
    def __init__(self, db: Session, oss: OSSStorage | None = None):
        self._db = db
        self._repo = FeedbackRepository(db)
        self._settings = get_settings()
        self._oss = oss or OSSStorage()
        self._rate_limiter = RateLimitService(db)

    # ------------------------------------------------------------------
    # Public: create feedback
    # ------------------------------------------------------------------

    def create_feedback(
        self,
        req: FeedbackCreateRequest,
        *,
        user_id: str | None = None,
        client_ip: str = "",
    ) -> FeedbackCreateResponse:
        """Create a feedback ticket and generate upload slots for attachments."""
        # Rate limit
        try:
            self._rate_limiter.check_feedback_create(
                self._settings.rate_limit_feedback_create_per_hour,
                3600,
                user_id=user_id,
                client_ip=client_ip,
            )
        except RateLimitError:
            raise FeedbackError("提交反馈过于频繁，请稍后再试。", status_code=429)

        # Validate attachments
        self._validate_attachments(req)

        # Serialize diagnostics
        diag_json = None
        if req.client_diagnostics:
            diag_json = json.dumps(req.client_diagnostics, ensure_ascii=False)

        # Create ticket
        ticket = FeedbackTicket(
            id=str(uuid4()),
            user_id=user_id,
            contact_email=req.contact_email,
            category=req.category,
            title=req.title,
            description=req.description,
            status="open",
            app_version=req.app_version,
            platform=req.platform,
            network_mode=req.network_mode,
            client_diagnostics_json=diag_json,
            attachment_count=len(req.attachments),
            total_size_bytes=sum(a.size_bytes for a in req.attachments),
        )
        self._repo.create_ticket(ticket, commit=False)

        # Create attachment records and upload slots
        slots: list[UploadSlot] = []
        now = utc_now()
        expires_at = now + timedelta(seconds=self._settings.feedback_attachment_url_expire_seconds)

        attachments: list[FeedbackAttachment] = []
        for att_init in req.attachments:
            att_id = str(uuid4())
            upload_id = str(uuid4())
            object_key = self._oss.build_feedback_object_key(
                ticket.id, att_id, att_init.filename
            )
            attachment = FeedbackAttachment(
                id=att_id,
                feedback_id=ticket.id,
                object_key=object_key,
                filename=att_init.filename,
                content_type=att_init.content_type,
                size_bytes=att_init.size_bytes,
                checksum_sha256=att_init.checksum_sha256,
                status="uploading",
                upload_id=upload_id,
                upload_expires_at=expires_at,
            )
            attachments.append(attachment)

            # Generate presigned PUT URL
            try:
                upload_url = self._oss.generate_put_url(
                    object_key,
                    expires_seconds=self._settings.feedback_attachment_url_expire_seconds,
                    content_type=att_init.content_type,
                )
            except OSSError as exc:
                logger.error("Failed to generate upload URL for feedback attachment: %s", exc)
                raise FeedbackError("生成附件上传链接失败，请稍后重试。") from exc

            slots.append(UploadSlot(
                attachment_id=att_id,
                upload_id=upload_id,
                upload_url=upload_url,
                expires_at=expires_at,
            ))

        if attachments:
            self._repo.create_attachments_batch(attachments, commit=False)

        self._db.commit()
        self._db.refresh(ticket)

        return FeedbackCreateResponse(
            id=ticket.id,
            status=ticket.status,
            upload_slots=slots,
        )

    # ------------------------------------------------------------------
    # Public: complete feedback (confirm uploads)
    # ------------------------------------------------------------------

    def complete_feedback(
        self,
        feedback_id: str,
        req: FeedbackCompleteRequest,
        *,
        client_ip: str = "",
    ) -> FeedbackCompleteResponse:
        """Verify uploaded attachments and finalize the feedback ticket."""
        ticket = self._repo.get_ticket(feedback_id)
        if ticket is None:
            raise FeedbackError("反馈不存在。", status_code=404)

        uploaded = 0
        failed = 0

        for upload_info in req.uploads:
            att = self._repo.get_attachment_by_upload_id(upload_info.upload_id)
            if att is None or att.feedback_id != feedback_id:
                failed += 1
                continue

            # Verify in OSS
            try:
                meta = self._oss.head_object(att.object_key)
                if meta["size"] != att.size_bytes:
                    logger.warning(
                        "Feedback attachment size mismatch: expected %d, got %d",
                        att.size_bytes, meta["size"],
                    )
                    self._repo.mark_failed(att)
                    failed += 1
                    continue
                self._repo.mark_uploaded(att)
                uploaded += 1
            except OSSError:
                logger.warning("Feedback attachment not found in OSS: %s", att.object_key)
                self._repo.mark_failed(att)
                failed += 1

        # Mark remaining uploading attachments as failed
        all_attachments = self._repo.list_attachments(feedback_id)
        for att in all_attachments:
            if att.status == "uploading":
                self._repo.mark_failed(att)
                failed += 1

        return FeedbackCompleteResponse(
            id=ticket.id,
            status=ticket.status,
            uploaded_attachments=uploaded,
            failed_attachments=failed,
        )

    # ------------------------------------------------------------------
    # Client: list user's own feedback
    # ------------------------------------------------------------------

    def list_user_feedback(
        self,
        user_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> ClientFeedbackListResponse:
        """List feedback submitted by an authenticated user."""
        tickets = self._repo.list_tickets(user_id=user_id, limit=limit, offset=offset)
        total = self._repo.count_tickets(user_id=user_id)
        ticket_ids = [t.id for t in tickets]
        reply_counts = self._repo.count_replies_batch(ticket_ids) if ticket_ids else {}
        return ClientFeedbackListResponse(
            items=[
                ClientFeedbackItem(
                    id=t.id,
                    category=t.category,
                    title=t.title,
                    description=t.description,
                    status=t.status,
                    priority=t.priority,
                    attachment_count=t.attachment_count,
                    reply_count=reply_counts.get(t.id, 0),
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in tickets
            ],
            total=total,
        )

    # ------------------------------------------------------------------
    # Admin: list / get / update / delete / download
    # ------------------------------------------------------------------

    def list_admin(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AdminFeedbackListResponse:
        tickets = self._repo.list_tickets(
            status=status, category=category, limit=limit, offset=offset
        )
        total = self._repo.count_tickets(status=status, category=category)
        # Batch-load reply counts to avoid N+1
        ticket_ids = [t.id for t in tickets]
        reply_counts = self._repo.count_replies_batch(ticket_ids) if ticket_ids else {}
        return AdminFeedbackListResponse(
            items=[self._to_admin_response(t, reply_counts.get(t.id, 0)) for t in tickets],
            total=total,
        )

    def get_admin(self, feedback_id: str) -> AdminFeedbackResponse:
        ticket = self._repo.get_ticket(feedback_id)
        if ticket is None:
            raise FeedbackError("反馈不存在。", status_code=404)
        reply_count = self._repo.count_replies(feedback_id)
        return self._to_admin_response(ticket, reply_count)

    def update_admin(
        self, feedback_id: str, req: AdminFeedbackUpdateRequest
    ) -> AdminFeedbackResponse:
        ticket = self._repo.get_ticket(feedback_id)
        if ticket is None:
            raise FeedbackError("反馈不存在。", status_code=404)

        values = req.model_dump(exclude_unset=True)
        if not values:
            raise FeedbackError("没有需要更新的字段。")

        self._repo.update_ticket(ticket, values)
        reply_count = self._repo.count_replies(feedback_id)
        return self._to_admin_response(ticket, reply_count)

    def get_download_url(
        self, feedback_id: str, attachment_id: str
    ) -> AdminDownloadUrlResponse:
        ticket = self._repo.get_ticket(feedback_id)
        if ticket is None:
            raise FeedbackError("反馈不存在。", status_code=404)

        att = self._repo.get_attachment(attachment_id)
        if att is None or att.feedback_id != feedback_id:
            raise FeedbackError("附件不存在。", status_code=404)
        if att.status != "uploaded":
            raise FeedbackError("附件未上传完成。")

        expire = self._settings.feedback_attachment_url_expire_seconds
        try:
            url = self._oss.generate_get_url(att.object_key, expires_seconds=expire)
        except OSSError as exc:
            raise FeedbackError("生成下载链接失败。") from exc

        return AdminDownloadUrlResponse(
            download_url=url,
            expires_at=utc_now() + timedelta(seconds=expire),
        )

    def delete_admin(self, feedback_id: str) -> None:
        """Soft-delete a feedback ticket and its attachments."""
        ticket = self._repo.get_ticket(feedback_id)
        if ticket is None:
            raise FeedbackError("反馈不存在。", status_code=404)

        # Soft-delete attachments and attempt OSS cleanup
        attachments = self._repo.list_attachments(feedback_id)
        for att in attachments:
            if att.status == "uploaded":
                try:
                    self._oss.delete_object(att.object_key)
                except OSSError:
                    logger.warning("Failed to delete OSS object: %s", att.object_key)
            self._repo.soft_delete_attachment(att, commit=False)

        self._repo.soft_delete_ticket(ticket)

    # ------------------------------------------------------------------
    # Privacy: anonymize user feedback on account deletion
    # ------------------------------------------------------------------

    def anonymize_user_feedback(self, user_id: str) -> int:
        """Remove user association from feedback and delete OSS attachments."""
        # Delete OSS objects for user's attachments
        attachments = self._repo.list_user_attachments(user_id)
        for att in attachments:
            try:
                self._oss.delete_object(att.object_key)
            except OSSError:
                logger.warning("Failed to delete OSS object during anonymization: %s", att.object_key)
            self._repo.soft_delete_attachment(att, commit=False)

        count = self._repo.anonymize_user_feedback(user_id, commit=False)
        if attachments or count:
            self._db.commit()
        return count

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_attachments(self, req: FeedbackCreateRequest) -> None:
        allowed_types = self._settings.feedback_allowed_content_type_set
        max_count = self._settings.feedback_max_attachments
        max_size = self._settings.feedback_max_attachment_size_bytes
        max_total = self._settings.feedback_max_total_size_bytes

        if len(req.attachments) > max_count:
            raise FeedbackError(f"附件数量不能超过 {max_count} 个。")

        total_size = 0
        for att in req.attachments:
            if att.content_type not in allowed_types:
                raise FeedbackError(f"不支持的附件类型: {att.content_type}")
            if att.size_bytes > max_size:
                raise FeedbackError(f"单个附件大小不能超过 {max_size // 1_048_576} MB。")
            total_size += att.size_bytes

        if total_size > max_total:
            raise FeedbackError(f"附件总大小不能超过 {max_total // 1_048_576} MB。")

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    def _to_admin_response(
        self, ticket: FeedbackTicket, reply_count: int = 0
    ) -> AdminFeedbackResponse:
        attachments = self._repo.list_attachments(ticket.id)
        diag = None
        if ticket.client_diagnostics_json:
            try:
                diag = json.loads(ticket.client_diagnostics_json)
            except (json.JSONDecodeError, TypeError):
                pass

        return AdminFeedbackResponse(
            id=ticket.id,
            user_id=ticket.user_id,
            contact_email=ticket.contact_email,
            category=ticket.category,
            title=ticket.title,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            app_version=ticket.app_version,
            platform=ticket.platform,
            network_mode=ticket.network_mode,
            client_diagnostics=diag,
            attachment_count=ticket.attachment_count,
            total_size_bytes=ticket.total_size_bytes,
            admin_note=ticket.admin_note,
            reply_count=reply_count,
            attachments=[
                AdminFeedbackAttachmentResponse(
                    id=a.id,
                    filename=a.filename,
                    content_type=a.content_type,
                    size_bytes=a.size_bytes,
                    status=a.status,
                    created_at=a.created_at,
                    uploaded_at=a.uploaded_at,
                )
                for a in attachments
            ],
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )

    # ------------------------------------------------------------------
    # Admin: reply management
    # ------------------------------------------------------------------

    def list_replies_admin(self, ticket_id: str) -> AdminFeedbackReplyListResponse:
        """List all replies for a feedback ticket (admin view)."""
        ticket = self._repo.get_ticket(ticket_id)
        if ticket is None:
            raise FeedbackError("反馈不存在。", status_code=404)
        replies = self._repo.list_replies(ticket_id)
        return AdminFeedbackReplyListResponse(
            items=[self._to_reply_response(r) for r in replies],
            total=len(replies),
        )

    def create_reply_admin(
        self,
        ticket_id: str,
        req: AdminFeedbackReplyCreateRequest,
        *,
        admin_user_id: str,
    ) -> FeedbackReplyResponse:
        """Create an admin reply to a feedback ticket."""
        ticket = self._repo.get_ticket(ticket_id)
        if ticket is None:
            raise FeedbackError("反馈不存在。", status_code=404)

        reply = FeedbackReply(
            id=str(uuid4()),
            ticket_id=ticket_id,
            author_id=admin_user_id,
            author_type="admin",
            content=req.content,
        )
        self._repo.create_reply(reply, commit=False)

        # Bump ticket updated_at so recently-replied tickets surface first
        ticket.updated_at = utc_now()
        self._db.commit()
        self._db.refresh(reply)

        return self._to_reply_response(reply)

    def delete_reply_admin(self, ticket_id: str, reply_id: str) -> None:
        """Soft-delete a reply."""
        ticket = self._repo.get_ticket(ticket_id)
        if ticket is None:
            raise FeedbackError("反馈不存在。", status_code=404)
        reply = self._repo.get_reply(reply_id)
        if reply is None or reply.ticket_id != ticket_id:
            raise FeedbackError("回复不存在。", status_code=404)
        self._repo.soft_delete_reply(reply)

    # ------------------------------------------------------------------
    # Reply response helper
    # ------------------------------------------------------------------

    def _to_reply_response(self, reply: FeedbackReply) -> FeedbackReplyResponse:
        display_name = None
        if reply.author_id:
            user = self._db.get(User, reply.author_id)
            if user:
                display_name = user.display_name
        return FeedbackReplyResponse(
            id=reply.id,
            ticket_id=reply.ticket_id,
            author_type=reply.author_type,
            author_display_name=display_name,
            content=reply.content,
            created_at=reply.created_at,
        )
