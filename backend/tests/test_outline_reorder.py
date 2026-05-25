"""Tests for outline drag-reorder functionality."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.outline_item import OutlineItem  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.schemas.outline import OutlineReorderItem  # noqa: E402
from app.services.outline_service import (  # noqa: E402
    OutlineCircularParentError,
    OutlineInvalidParentError,
    OutlineNotFoundError,
    OutlineParentNotFoundError,
    OutlineService,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_project(db_session):
    project_id = str(uuid4())
    now = datetime.now(timezone.utc)
    project = Project(id=project_id, title="测试项目", created_at=now, updated_at=now)
    db_session.add(project)
    db_session.commit()
    return project_id


def _make_outline(db_session, project_id, title, parent_id=None, order_index=0):
    outline_id = str(uuid4())
    now = datetime.now(timezone.utc)
    outline = OutlineItem(
        id=outline_id,
        project_id=project_id,
        parent_id=parent_id,
        title=title,
        item_type="note",
        status="planned",
        order_index=order_index,
        importance="normal",
        created_at=now,
        updated_at=now,
    )
    db_session.add(outline)
    db_session.commit()
    return outline_id


class TestOutlineReorder:
    def test_reorder_same_level(self, db_session):
        project_id = _make_project(db_session)
        a = _make_outline(db_session, project_id, "A", order_index=0)
        b = _make_outline(db_session, project_id, "B", order_index=1)
        c = _make_outline(db_session, project_id, "C", order_index=2)

        service = OutlineService(db_session)
        items = [
            OutlineReorderItem(outline_id=c, order_index=0),
            OutlineReorderItem(outline_id=a, order_index=1),
            OutlineReorderItem(outline_id=b, order_index=2),
        ]
        updated = service.reorder_outlines(project_id, items)
        assert updated == 3

        outlines = service.list_project_outlines(project_id)
        titles = [o.title for o in outlines]
        assert titles == ["C", "A", "B"]

    def test_move_to_child(self, db_session):
        project_id = _make_project(db_session)
        parent = _make_outline(db_session, project_id, "Parent", order_index=0)
        child = _make_outline(db_session, project_id, "Child", order_index=1)

        service = OutlineService(db_session)
        items = [
            OutlineReorderItem(outline_id=child, parent_id=parent, order_index=0),
        ]
        updated = service.reorder_outlines(project_id, items)
        assert updated == 1

        outlines = service.list_project_outlines(project_id)
        child_item = next(o for o in outlines if o.id == child)
        assert child_item.parent_id == parent

    def test_self_parent_rejected(self, db_session):
        project_id = _make_project(db_session)
        a = _make_outline(db_session, project_id, "A", order_index=0)

        service = OutlineService(db_session)
        items = [
            OutlineReorderItem(outline_id=a, parent_id=a, order_index=0),
        ]
        with pytest.raises(OutlineInvalidParentError):
            service.reorder_outlines(project_id, items)

    def test_circular_parent_rejected(self, db_session):
        project_id = _make_project(db_session)
        a = _make_outline(db_session, project_id, "A", order_index=0)
        b = _make_outline(db_session, project_id, "B", parent_id=a, order_index=0)

        service = OutlineService(db_session)
        # Try to make A a child of B (B is already a child of A)
        items = [
            OutlineReorderItem(outline_id=a, parent_id=b, order_index=0),
        ]
        with pytest.raises(OutlineCircularParentError):
            service.reorder_outlines(project_id, items)

    def test_unknown_outline_rejected(self, db_session):
        project_id = _make_project(db_session)
        _make_outline(db_session, project_id, "A", order_index=0)

        service = OutlineService(db_session)
        items = [
            OutlineReorderItem(outline_id=str(uuid4()), order_index=0),
        ]
        with pytest.raises(OutlineNotFoundError):
            service.reorder_outlines(project_id, items)

    def test_unknown_parent_rejected(self, db_session):
        project_id = _make_project(db_session)
        a = _make_outline(db_session, project_id, "A", order_index=0)

        service = OutlineService(db_session)
        items = [
            OutlineReorderItem(outline_id=a, parent_id=str(uuid4()), order_index=0),
        ]
        with pytest.raises(OutlineParentNotFoundError):
            service.reorder_outlines(project_id, items)
