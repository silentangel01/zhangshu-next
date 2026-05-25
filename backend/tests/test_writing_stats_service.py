"""Tests for the writing statistics service."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.chapter import Chapter  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.volume import Volume  # noqa: E402
from app.models.writing_stat_event import WritingStatEvent  # noqa: E402
from app.services.writing_stats_service import (  # noqa: E402
    WritingStatsProjectNotFoundError,
    WritingStatsService,
)


def _local_now() -> datetime:
    return datetime.now().astimezone()


def _utc(delta_hours: int = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=delta_hours)


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
    project = Project(id=pid, title="测试作品", target_word_count=100000)
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def service(db_session):
    return WritingStatsService(db_session)


def _add_chapter(db_session, project_id, *, title="章节", word_count=0, volume_id=None, deleted=False):
    cid = str(uuid4())
    chapter = Chapter(
        id=cid,
        project_id=project_id,
        volume_id=volume_id,
        title=title,
        content="x" * word_count,
        word_count=word_count,
        order_index=0,
    )
    if deleted:
        chapter.deleted_at = datetime.now(timezone.utc)
    db_session.add(chapter)
    db_session.commit()
    return chapter


def _add_volume(db_session, project_id, title="分卷"):
    vid = str(uuid4())
    volume = Volume(id=vid, project_id=project_id, title=title, order_index=0)
    db_session.add(volume)
    db_session.commit()
    return volume


def _add_event(db_session, project_id, chapter_id, *, delta=100, local_date=None, local_hour=None, volume_id=None):
    now = _local_now()
    eid = str(uuid4())
    event = WritingStatEvent(
        id=eid,
        project_id=project_id,
        chapter_id=chapter_id,
        volume_id=volume_id,
        source="manual",
        old_word_count=0,
        new_word_count=abs(delta),
        delta_words=delta,
        added_words=max(delta, 0),
        deleted_words=max(-delta, 0),
        occurred_at=now,
        local_date=local_date or now.strftime("%Y-%m-%d"),
        local_hour=local_hour if local_hour is not None else now.hour,
    )
    db_session.add(event)
    db_session.commit()
    return event


# ------------------------------------------------------------------
# Project not found
# ------------------------------------------------------------------


class TestProjectNotFound:
    def test_raises_when_project_missing(self, db_session, service):
        with pytest.raises(WritingStatsProjectNotFoundError):
            service.get_overview(str(uuid4()))


# ------------------------------------------------------------------
# Total words
# ------------------------------------------------------------------


class TestTotalWords:
    def test_sums_only_active_chapters(self, db_session, project, service):
        _add_chapter(db_session, project.id, word_count=500)
        _add_chapter(db_session, project.id, word_count=300)
        _add_chapter(db_session, project.id, word_count=1000, deleted=True)

        overview = service.get_overview(project.id)
        assert overview.total_words == 800

    def test_zero_when_no_chapters(self, db_session, project, service):
        overview = service.get_overview(project.id)
        assert overview.total_words == 0


# ------------------------------------------------------------------
# Target / progress
# ------------------------------------------------------------------


class TestProgress:
    def test_progress_with_target(self, db_session, project, service):
        _add_chapter(db_session, project.id, word_count=40000)
        overview = service.get_overview(project.id)
        assert overview.target_words == 100000
        assert overview.progress_percent == 40.0

    def test_progress_without_target(self, db_session, db_session_fixture_hack=None):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        pid = str(uuid4())
        proj = Project(id=pid, title="无目标")
        session.add(proj)
        session.commit()

        svc = WritingStatsService(session)
        overview = svc.get_overview(pid)
        assert overview.target_words is None
        assert overview.progress_percent is None
        session.close()

    def test_progress_capped_at_100(self, db_session, project, service):
        _add_chapter(db_session, project.id, word_count=200000)
        overview = service.get_overview(project.id)
        assert overview.progress_percent == 100.0


# ------------------------------------------------------------------
# Record chapter word change
# ------------------------------------------------------------------


class TestRecordChapterWordChange:
    def test_records_positive_delta(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id, word_count=0)
        event = service.record_chapter_word_change(
            project_id=project.id,
            chapter_id=chapter.id,
            volume_id=None,
            source="manual",
            old_word_count=0,
            new_word_count=500,
            occurred_at=datetime.now(timezone.utc),
        )
        assert event is not None
        assert event.delta_words == 500
        assert event.added_words == 500
        assert event.deleted_words == 0

    def test_records_negative_delta(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id, word_count=500)
        event = service.record_chapter_word_change(
            project_id=project.id,
            chapter_id=chapter.id,
            volume_id=None,
            source="manual",
            old_word_count=500,
            new_word_count=200,
            occurred_at=datetime.now(timezone.utc),
        )
        assert event is not None
        assert event.delta_words == -300
        assert event.added_words == 0
        assert event.deleted_words == 300

    def test_returns_none_when_no_change(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id, word_count=500)
        event = service.record_chapter_word_change(
            project_id=project.id,
            chapter_id=chapter.id,
            volume_id=None,
            source="manual",
            old_word_count=500,
            new_word_count=500,
            occurred_at=datetime.now(timezone.utc),
        )
        assert event is None

    def test_local_date_and_hour_are_set(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id, word_count=0)
        now = datetime.now(timezone.utc)
        event = service.record_chapter_word_change(
            project_id=project.id,
            chapter_id=chapter.id,
            volume_id=None,
            source="autosave",
            old_word_count=0,
            new_word_count=100,
            occurred_at=now,
        )
        assert event is not None
        local_now = now.astimezone()
        assert event.local_date == local_now.strftime("%Y-%m-%d")
        assert event.local_hour == local_now.hour
        assert event.source == "autosave"


# ------------------------------------------------------------------
# Today / week / month aggregation
# ------------------------------------------------------------------


class TestPeriodAggregation:
    def test_today_net_words(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id)
        today_str = _local_now().strftime("%Y-%m-%d")
        _add_event(db_session, project.id, chapter.id, delta=500, local_date=today_str)
        _add_event(db_session, project.id, chapter.id, delta=-100, local_date=today_str)

        overview = service.get_overview(project.id)
        assert overview.today_net_words == 400

    def test_week_net_words(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id)
        today = _local_now().date()
        for i in range(7):
            day_str = (today - timedelta(days=i)).isoformat()
            _add_event(db_session, project.id, chapter.id, delta=100, local_date=day_str)

        overview = service.get_overview(project.id)
        assert overview.week_net_words == 700

    def test_month_net_words(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id)
        today = _local_now().date()
        for i in range(30):
            day_str = (today - timedelta(days=i)).isoformat()
            _add_event(db_session, project.id, chapter.id, delta=50, local_date=day_str)

        overview = service.get_overview(project.id)
        assert overview.month_net_words == 1500

    def test_old_events_excluded_from_today(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id)
        old_date = (_local_now().date() - timedelta(days=10)).isoformat()
        _add_event(db_session, project.id, chapter.id, delta=9999, local_date=old_date)

        overview = service.get_overview(project.id)
        assert overview.today_net_words == 0


# ------------------------------------------------------------------
# Streak calculation
# ------------------------------------------------------------------


class TestStreakCalculation:
    def test_current_streak_consecutive_days(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id)
        today = _local_now().date()
        for i in range(5):
            day_str = (today - timedelta(days=i)).isoformat()
            _add_event(db_session, project.id, chapter.id, delta=100, local_date=day_str)

        overview = service.get_overview(project.id)
        assert overview.current_streak_days == 5

    def test_negative_delta_day_still_counts(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id)
        today = _local_now().date()
        _add_event(db_session, project.id, chapter.id, delta=100, local_date=today.isoformat())
        yesterday = (today - timedelta(days=1)).isoformat()
        _add_event(db_session, project.id, chapter.id, delta=-50, local_date=yesterday)

        overview = service.get_overview(project.id)
        assert overview.current_streak_days == 2

    def test_gap_breaks_streak(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id)
        today = _local_now().date()
        _add_event(db_session, project.id, chapter.id, delta=100, local_date=today.isoformat())
        # Skip yesterday, add 2 days ago
        two_days_ago = (today - timedelta(days=2)).isoformat()
        _add_event(db_session, project.id, chapter.id, delta=100, local_date=two_days_ago)

        overview = service.get_overview(project.id)
        assert overview.current_streak_days == 1

    def test_longest_streak(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id)
        today = _local_now().date()
        # Current streak: 2 days
        _add_event(db_session, project.id, chapter.id, delta=100, local_date=today.isoformat())
        _add_event(db_session, project.id, chapter.id, delta=100, local_date=(today - timedelta(days=1)).isoformat())
        # Gap
        # Old streak: 5 days
        for i in range(5):
            day_str = (today - timedelta(days=5 + i)).isoformat()
            _add_event(db_session, project.id, chapter.id, delta=100, local_date=day_str)

        overview = service.get_overview(project.id)
        assert overview.current_streak_days == 2
        assert overview.longest_streak_days == 5

    def test_no_events_zero_streak(self, db_session, project, service):
        overview = service.get_overview(project.id)
        assert overview.current_streak_days == 0
        assert overview.longest_streak_days == 0


# ------------------------------------------------------------------
# Volume breakdown
# ------------------------------------------------------------------


class TestVolumeBreakdown:
    def test_includes_unassigned_volume(self, db_session, project, service):
        _add_chapter(db_session, project.id, word_count=200)
        overview = service.get_overview(project.id)
        assert len(overview.volume_breakdown) == 1
        assert overview.volume_breakdown[0].title == "未分卷"
        assert overview.volume_breakdown[0].total_words == 200

    def test_groups_by_volume(self, db_session, project, service):
        vol = _add_volume(db_session, project.id, title="第一卷")
        _add_chapter(db_session, project.id, word_count=300, volume_id=vol.id)
        _add_chapter(db_session, project.id, word_count=200, volume_id=vol.id)
        _add_chapter(db_session, project.id, word_count=100)

        overview = service.get_overview(project.id)
        vol_map = {item.title: item for item in overview.volume_breakdown}
        assert "第一卷" in vol_map
        assert vol_map["第一卷"].total_words == 500
        assert vol_map["第一卷"].chapter_count == 2
        assert "未分卷" in vol_map
        assert vol_map["未分卷"].total_words == 100


# ------------------------------------------------------------------
# Chapter rankings
# ------------------------------------------------------------------


class TestChapterRankings:
    def test_sorted_by_7d_delta(self, db_session, project, service):
        chapter_a = _add_chapter(db_session, project.id, title="章节A", word_count=1000)
        chapter_b = _add_chapter(db_session, project.id, title="章节B", word_count=2000)
        today_str = _local_now().strftime("%Y-%m-%d")
        _add_event(db_session, project.id, chapter_a.id, delta=500, local_date=today_str)
        _add_event(db_session, project.id, chapter_b.id, delta=1200, local_date=today_str)

        overview = service.get_overview(project.id)
        assert len(overview.chapter_rankings) == 2
        assert overview.chapter_rankings[0].chapter_id == chapter_b.id
        assert overview.chapter_rankings[0].delta_words_7d == 1200
        assert overview.chapter_rankings[1].chapter_id == chapter_a.id

    def test_excludes_deleted_chapters(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id, word_count=500)
        deleted_chapter = _add_chapter(db_session, project.id, word_count=800, deleted=True)
        today_str = _local_now().strftime("%Y-%m-%d")
        _add_event(db_session, project.id, chapter.id, delta=200, local_date=today_str)
        _add_event(db_session, project.id, deleted_chapter.id, delta=9999, local_date=today_str)

        overview = service.get_overview(project.id)
        ranking_ids = [item.chapter_id for item in overview.chapter_rankings]
        assert chapter.id in ranking_ids
        assert deleted_chapter.id not in ranking_ids


# ------------------------------------------------------------------
# Warnings
# ------------------------------------------------------------------


class TestWarnings:
    def test_warning_when_no_events(self, db_session, project, service):
        overview = service.get_overview(project.id)
        assert len(overview.warnings) > 0
        assert "统计" in overview.warnings[0] or "记录" in overview.warnings[0]

    def test_no_warning_when_events_exist(self, db_session, project, service):
        chapter = _add_chapter(db_session, project.id)
        today_str = _local_now().strftime("%Y-%m-%d")
        _add_event(db_session, project.id, chapter.id, delta=100, local_date=today_str)

        overview = service.get_overview(project.id)
        assert len(overview.warnings) == 0


# ------------------------------------------------------------------
# Active minutes estimation
# ------------------------------------------------------------------


class TestActiveMinutesEstimation:
    def test_no_events_zero_minutes(self):
        assert WritingStatsService._estimate_active_minutes([]) == 0

    def test_single_event_one_minute(self, db_session, project):
        chapter = _add_chapter(db_session, project.id)
        event = WritingStatEvent(
            id=str(uuid4()),
            project_id=project.id,
            chapter_id=chapter.id,
            source="manual",
            old_word_count=0,
            new_word_count=100,
            delta_words=100,
            added_words=100,
            deleted_words=0,
            occurred_at=datetime.now(timezone.utc),
            local_date=_local_now().strftime("%Y-%m-%d"),
            local_hour=_local_now().hour,
        )
        assert WritingStatsService._estimate_active_minutes([event]) == 1

    def test_two_events_within_gap(self, db_session, project):
        chapter = _add_chapter(db_session, project.id)
        now = datetime.now(timezone.utc)
        events = [
            WritingStatEvent(
                id=str(uuid4()),
                project_id=project.id,
                chapter_id=chapter.id,
                source="manual",
                old_word_count=0,
                new_word_count=100,
                delta_words=100,
                added_words=100,
                deleted_words=0,
                occurred_at=now,
                local_date="",
                local_hour=0,
            ),
            WritingStatEvent(
                id=str(uuid4()),
                project_id=project.id,
                chapter_id=chapter.id,
                source="manual",
                old_word_count=100,
                new_word_count=200,
                delta_words=100,
                added_words=100,
                deleted_words=0,
                occurred_at=now + timedelta(minutes=3),
                local_date="",
                local_hour=0,
            ),
        ]
        minutes = WritingStatsService._estimate_active_minutes(events)
        assert minutes == 3

    def test_two_events_exceeding_gap(self, db_session, project):
        chapter = _add_chapter(db_session, project.id)
        now = datetime.now(timezone.utc)
        events = [
            WritingStatEvent(
                id=str(uuid4()),
                project_id=project.id,
                chapter_id=chapter.id,
                source="manual",
                old_word_count=0,
                new_word_count=100,
                delta_words=100,
                added_words=100,
                deleted_words=0,
                occurred_at=now,
                local_date="",
                local_hour=0,
            ),
            WritingStatEvent(
                id=str(uuid4()),
                project_id=project.id,
                chapter_id=chapter.id,
                source="manual",
                old_word_count=100,
                new_word_count=200,
                delta_words=100,
                added_words=100,
                deleted_words=0,
                occurred_at=now + timedelta(minutes=10),
                local_date="",
                local_hour=0,
            ),
        ]
        minutes = WritingStatsService._estimate_active_minutes(events)
        # Two separate sessions, each at least 1 minute
        assert minutes == 2


# ------------------------------------------------------------------
# Streak calculation unit tests
# ------------------------------------------------------------------


class TestStreakUnit:
    def test_empty_dates(self):
        today = _local_now().date()
        current, longest = WritingStatsService._calculate_streaks([], today)
        assert current == 0
        assert longest == 0

    def test_single_today(self):
        today = _local_now().date()
        current, longest = WritingStatsService._calculate_streaks([today.isoformat()], today)
        assert current == 1
        assert longest == 1

    def test_three_consecutive_ending_today(self):
        today = _local_now().date()
        dates = [(today - timedelta(days=i)).isoformat() for i in range(3)]
        current, longest = WritingStatsService._calculate_streaks(dates, today)
        assert current == 3
        assert longest == 3

    def test_gap_in_middle(self):
        today = _local_now().date()
        dates = [
            today.isoformat(),
            (today - timedelta(days=1)).isoformat(),
            # gap: skip day 2
            (today - timedelta(days=3)).isoformat(),
            (today - timedelta(days=4)).isoformat(),
            (today - timedelta(days=5)).isoformat(),
        ]
        current, longest = WritingStatsService._calculate_streaks(dates, today)
        assert current == 2
        assert longest == 3
