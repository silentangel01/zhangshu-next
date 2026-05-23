"""Tests for the creative reminder service."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.chapter import Chapter  # noqa: E402
from app.models.clue import Clue  # noqa: E402
from app.models.chapter_clue import ChapterClue  # noqa: E402
from app.models.character import Character  # noqa: E402
from app.models.chapter_character import ChapterCharacter  # noqa: E402
from app.models.outline_item import OutlineItem  # noqa: E402
from app.models.timeline_event import TimelineEvent  # noqa: E402
from app.models.graph_node import GraphNode  # noqa: E402
from app.models.setting_item import SettingItem  # noqa: E402
from app.models.chapter_setting import ChapterSetting  # noqa: E402
from app.models.volume import Volume  # noqa: E402
from app.models.timeline_track import TimelineTrack  # noqa: E402
from app.services.creative_reminder_service import (  # noqa: E402
    CreativeReminderProjectNotFoundError,
    CreativeReminderService,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def project(db_session):
    pid = str(uuid4())
    project = Project(id=pid, title="Test Project")
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def service(db_session):
    return CreativeReminderService(db_session)


def _make_chapters(db_session, project_id, count):
    """Create `count` chapters with sequential order_index and return their ids."""
    ids = []
    for i in range(count):
        cid = str(uuid4())
        chapter = Chapter(
            id=cid,
            project_id=project_id,
            title=f"Chapter {i + 1}",
            order_index=i,
        )
        db_session.add(chapter)
        ids.append(cid)
    db_session.commit()
    return ids


# ---------- Tests ----------


class TestProjectNotFound:
    def test_raises_when_project_missing(self, db_session, service):
        with pytest.raises(CreativeReminderProjectNotFoundError):
            service.list_project_reminders(str(uuid4()))


class TestImportantClueUnresolved:
    def test_critical_clue_long_gap(self, db_session, project, service):
        chapter_ids = _make_chapters(db_session, project.id, 25)

        clue_id = str(uuid4())
        clue = Clue(
            id=clue_id,
            project_id=project.id,
            title="神秘符号",
            importance="critical",
            status="planted",
            setup_chapter_id=chapter_ids[0],
            payoff_chapter_id=None,
        )
        db_session.add(clue)
        db_session.commit()

        reminders = service.list_project_reminders(project.id)
        clue_reminders = [r for r in reminders if r.type == "important_clue_unresolved"]

        assert len(clue_reminders) == 1
        r = clue_reminders[0]
        assert r.severity == "critical"
        assert r.target_id == clue_id
        assert r.reason  # non-empty
        assert r.suggestion  # non-empty
        assert r.scope_label == "全书"


class TestSettingUsedButDraft:
    def test_draft_setting_linked_to_chapter(self, db_session, project, service):
        chapter_ids = _make_chapters(db_session, project.id, 2)

        setting_id = str(uuid4())
        setting = SettingItem(
            id=setting_id,
            project_id=project.id,
            title="未定稿魔法体系",
            item_type="custom",
            canon_status="draft",
            node_kind="page",
        )
        db_session.add(setting)

        relation = ChapterSetting(
            id=str(uuid4()),
            project_id=project.id,
            chapter_id=chapter_ids[0],
            setting_item_id=setting_id,
        )
        db_session.add(relation)
        db_session.commit()

        reminders = service.list_project_reminders(project.id)
        draft_reminders = [r for r in reminders if r.type == "setting_used_but_draft"]

        assert len(draft_reminders) == 1
        r = draft_reminders[0]
        assert r.severity == "info"
        assert r.target_id == setting_id
        assert r.scope_label == "关联章节"


class TestSeverityFilter:
    def test_filter_by_severity(self, db_session, project, service):
        """Create both a critical clue reminder and an info setting reminder,
        then verify severity filter isolates them."""
        chapter_ids = _make_chapters(db_session, project.id, 25)

        # Critical clue
        clue = Clue(
            id=str(uuid4()),
            project_id=project.id,
            title="关键伏笔",
            importance="critical",
            status="planted",
            setup_chapter_id=chapter_ids[0],
        )
        db_session.add(clue)

        # Info: draft setting
        setting_id = str(uuid4())
        setting = SettingItem(
            id=setting_id,
            project_id=project.id,
            title="草稿设定",
            item_type="custom",
            canon_status="draft",
            node_kind="page",
        )
        db_session.add(setting)
        db_session.add(
            ChapterSetting(
                id=str(uuid4()),
                project_id=project.id,
                chapter_id=chapter_ids[0],
                setting_item_id=setting_id,
            )
        )
        db_session.commit()

        critical_only = service.list_project_reminders(project.id, severity="critical")
        assert all(r.severity == "critical" for r in critical_only)
        assert len(critical_only) >= 1

        info_only = service.list_project_reminders(project.id, severity="info")
        assert all(r.severity == "info" for r in info_only)
        assert len(info_only) >= 1


class TestReminderTypeFilter:
    def test_filter_by_reminder_type(self, db_session, project, service):
        chapter_ids = _make_chapters(db_session, project.id, 25)

        # Clue reminder
        clue = Clue(
            id=str(uuid4()),
            project_id=project.id,
            title="伏笔A",
            importance="critical",
            status="planted",
            setup_chapter_id=chapter_ids[0],
        )
        db_session.add(clue)

        # Setting reminder
        setting_id = str(uuid4())
        setting = SettingItem(
            id=setting_id,
            project_id=project.id,
            title="草稿设定B",
            item_type="custom",
            canon_status="draft",
            node_kind="page",
        )
        db_session.add(setting)
        db_session.add(
            ChapterSetting(
                id=str(uuid4()),
                project_id=project.id,
                chapter_id=chapter_ids[0],
                setting_item_id=setting_id,
            )
        )
        db_session.commit()

        clue_reminders = service.list_project_reminders(
            project.id, reminder_type="important_clue_unresolved"
        )
        assert len(clue_reminders) >= 1
        assert all(r.type == "important_clue_unresolved" for r in clue_reminders)

        setting_reminders = service.list_project_reminders(
            project.id, reminder_type="setting_used_but_draft"
        )
        assert len(setting_reminders) >= 1
        assert all(r.type == "setting_used_but_draft" for r in setting_reminders)


class TestSeveritySorting:
    def test_sorted_critical_before_warning_before_info(self, db_session, project, service):
        """Create reminders of all three severities and verify sort order."""
        chapter_ids = _make_chapters(db_session, project.id, 25)

        # info: draft setting
        setting_id = str(uuid4())
        setting = SettingItem(
            id=setting_id,
            project_id=project.id,
            title="草稿设定",
            item_type="custom",
            canon_status="draft",
            node_kind="page",
        )
        db_session.add(setting)
        db_session.add(
            ChapterSetting(
                id=str(uuid4()),
                project_id=project.id,
                chapter_id=chapter_ids[0],
                setting_item_id=setting_id,
            )
        )

        # warning: high-importance timeline event with no chapter
        event = TimelineEvent(
            id=str(uuid4()),
            project_id=project.id,
            title="关键事件",
            importance="high",
            chapter_id=None,
        )
        db_session.add(event)

        # critical: critical clue unresolved
        clue = Clue(
            id=str(uuid4()),
            project_id=project.id,
            title="核心伏笔",
            importance="critical",
            status="planted",
            setup_chapter_id=chapter_ids[0],
        )
        db_session.add(clue)
        db_session.commit()

        reminders = service.list_project_reminders(project.id)
        severities = [r.severity for r in reminders]

        # Verify order: all criticals come before warnings, all warnings before infos
        severity_rank = {"critical": 0, "warning": 1, "info": 2}
        ranks = [severity_rank[s] for s in severities]
        assert ranks == sorted(ranks), f"Expected sorted severities, got {severities}"

        # Verify we actually have all three levels
        assert "critical" in severities
        assert "warning" in severities
        assert "info" in severities
