from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.writing_stat_event import WritingStatEvent
from app.repositories.chapter_repo import ChapterRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.volume_repo import VolumeRepository
from app.repositories.writing_stats_repo import WritingStatsRepository
from app.schemas.writing_stats import (
    WritingStatsChapterRankingItem,
    WritingStatsDailyPoint,
    WritingStatsHourlyPoint,
    WritingStatsOverview,
    WritingStatsVolumeBreakdownItem,
)


ACTIVE_SESSION_GAP_MINUTES = 5
ISOLATED_EVENT_MINUTES = 1
TOP_CHAPTER_LIMIT = 20


def _local_now() -> datetime:
    return datetime.now().astimezone()


def _local_today() -> date:
    return _local_now().date()


def _format_date(value: date) -> str:
    return value.isoformat()


class WritingStatsProjectNotFoundError(Exception):
    pass


class WritingStatsService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.chapter_repo = ChapterRepository(db)
        self.volume_repo = VolumeRepository(db)
        self.stats_repo = WritingStatsRepository(db)

    # ------------------------------------------------------------------
    # Event recording
    # ------------------------------------------------------------------

    def record_chapter_word_change(
        self,
        *,
        project_id: str,
        chapter_id: str,
        volume_id: str | None,
        source: str,
        old_word_count: int,
        new_word_count: int,
        occurred_at: datetime,
    ) -> WritingStatEvent | None:
        delta = new_word_count - old_word_count
        if delta == 0:
            return None

        try:
            local_occurred = occurred_at.astimezone()
        except (ValueError, OSError):
            local_occurred = occurred_at.replace(tzinfo=timezone.utc).astimezone()

        event = WritingStatEvent(
            id=str(uuid4()),
            project_id=project_id,
            chapter_id=chapter_id,
            volume_id=volume_id,
            source=source,
            old_word_count=old_word_count,
            new_word_count=new_word_count,
            delta_words=delta,
            added_words=max(delta, 0),
            deleted_words=max(-delta, 0),
            occurred_at=occurred_at,
            local_date=local_occurred.strftime("%Y-%m-%d"),
            local_hour=local_occurred.hour,
        )
        return self.stats_repo.create_event(event, commit=False)

    # ------------------------------------------------------------------
    # Overview aggregation
    # ------------------------------------------------------------------

    def get_overview(
        self,
        project_id: str,
        days: int = 90,
    ) -> WritingStatsOverview:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise WritingStatsProjectNotFoundError

        today = _local_today()
        today_str = _format_date(today)
        range_start_str = _format_date(today - timedelta(days=days))
        week_start_str = _format_date(today - timedelta(days=6))
        month_start_str = _format_date(today - timedelta(days=29))
        last_7d_start_str = _format_date(today - timedelta(days=6))

        # --- total words from active chapters ---
        active_chapters = self.chapter_repo.list_active_by_project(project_id)
        total_words = sum(chapter.word_count for chapter in active_chapters)

        # --- target / progress ---
        target_words = project.target_word_count
        progress_percent: float | None = None
        if target_words and target_words > 0:
            progress_percent = round(
                min(total_words / target_words * 100, 100.0),
                1,
            )

        # --- daily aggregation ---
        daily_rows = self.stats_repo.aggregate_daily(
            project_id,
            range_start_str,
            today_str,
        )
        daily_map: dict[str, dict] = {}
        for row in daily_rows:
            daily_map[row.local_date] = {
                "net_words": int(row.net_words or 0),
                "added_words": int(row.added_words or 0),
                "deleted_words": int(row.deleted_words or 0),
                "event_count": int(row.event_count or 0),
            }

        # --- hourly aggregation ---
        hourly_rows = self.stats_repo.aggregate_hourly(
            project_id,
            range_start_str,
            today_str,
        )

        # --- today / week / month net words ---
        today_net = daily_map.get(today_str, {}).get("net_words", 0)

        week_net = sum(
            info["net_words"]
            for date_str, info in daily_map.items()
            if date_str >= week_start_str
        )
        month_net = sum(
            info["net_words"]
            for date_str, info in daily_map.items()
            if date_str >= month_start_str
        )

        # --- streak ---
        all_event_dates = self.stats_repo.list_event_dates(project_id)
        current_streak, longest_streak = self._calculate_streaks(all_event_dates, today)

        # --- today's active minutes estimation ---
        today_events = self.stats_repo.list_events_by_project_in_range(
            project_id,
            today_str,
            today_str,
        )
        today_minutes = self._estimate_active_minutes(today_events)
        today_wph = round(today_net / (today_minutes / 60), 1) if today_minutes > 0 else 0.0

        # --- build daily points with per-day active minutes ---
        daily_points: list[WritingStatsDailyPoint] = []
        for day_offset in range(days):
            day = today - timedelta(days=days - 1 - day_offset)
            day_str = _format_date(day)
            info = daily_map.get(day_str)
            if info is None:
                daily_points.append(
                    WritingStatsDailyPoint(
                        date=day_str,
                        net_words=0,
                        added_words=0,
                        deleted_words=0,
                        event_count=0,
                        active_minutes_estimated=0,
                    )
                )
            else:
                day_events = self.stats_repo.list_events_by_project_in_range(
                    project_id,
                    day_str,
                    day_str,
                )
                daily_points.append(
                    WritingStatsDailyPoint(
                        date=day_str,
                        net_words=info["net_words"],
                        added_words=info["added_words"],
                        deleted_words=info["deleted_words"],
                        event_count=info["event_count"],
                        active_minutes_estimated=self._estimate_active_minutes(day_events),
                    )
                )

        # --- build hourly points ---
        hourly_points: list[WritingStatsHourlyPoint] = []
        hourly_map: dict[int, dict] = {}
        for row in hourly_rows:
            hourly_map[int(row.local_hour)] = {
                "net_words": int(row.net_words or 0),
                "event_count": int(row.event_count or 0),
            }
        for hour in range(24):
            info = hourly_map.get(hour)
            hourly_points.append(
                WritingStatsHourlyPoint(
                    hour=hour,
                    net_words=info["net_words"] if info else 0,
                    event_count=info["event_count"] if info else 0,
                )
            )

        # --- volume breakdown ---
        volumes = self.volume_repo.list_active_by_project(project_id)
        volume_title_map: dict[str, str] = {vol.id: vol.title for vol in volumes}
        volume_chapters: dict[str | None, list] = {}
        for chapter in active_chapters:
            volume_chapters.setdefault(chapter.volume_id, []).append(chapter)

        volume_breakdown: list[WritingStatsVolumeBreakdownItem] = []
        for vol in volumes:
            chapters_in_vol = volume_chapters.get(vol.id, [])
            volume_breakdown.append(
                WritingStatsVolumeBreakdownItem(
                    volume_id=vol.id,
                    title=vol.title,
                    total_words=sum(ch.word_count for ch in chapters_in_vol),
                    chapter_count=len(chapters_in_vol),
                )
            )
        unassigned = volume_chapters.get(None, [])
        if unassigned:
            volume_breakdown.append(
                WritingStatsVolumeBreakdownItem(
                    volume_id=None,
                    title="未分卷",
                    total_words=sum(ch.word_count for ch in unassigned),
                    chapter_count=len(unassigned),
                )
            )

        # --- chapter rankings (by 7-day delta) ---
        chapter_delta_rows = self.stats_repo.aggregate_chapter_delta(
            project_id,
            last_7d_start_str,
            today_str,
        )
        chapter_delta_map: dict[str, int] = {
            row.chapter_id: int(row.delta_words or 0) for row in chapter_delta_rows
        }

        chapter_map = {ch.id: ch for ch in active_chapters}
        ranked_ids = sorted(
            chapter_delta_map.keys(),
            key=lambda cid: chapter_delta_map[cid],
            reverse=True,
        )[:TOP_CHAPTER_LIMIT]

        chapter_rankings: list[WritingStatsChapterRankingItem] = []
        for cid in ranked_ids:
            chapter = chapter_map.get(cid)
            if chapter is None:
                continue
            vol_title = (
                volume_title_map.get(chapter.volume_id, "未分卷")
                if chapter.volume_id
                else "未分卷"
            )
            chapter_rankings.append(
                WritingStatsChapterRankingItem(
                    chapter_id=chapter.id,
                    title=chapter.title,
                    volume_id=chapter.volume_id,
                    volume_title=vol_title,
                    total_words=chapter.word_count,
                    delta_words_7d=chapter_delta_map[cid],
                    updated_at=chapter.updated_at,
                )
            )

        # --- warnings ---
        warnings: list[str] = []
        if not all_event_dates:
            warnings.append("写作趋势从统计功能启用后开始记录，历史正文不会回填到每日净增。")

        # --- average daily words (last 30 days) ---
        days_with_data = sum(
            1
            for date_str, info in daily_map.items()
            if date_str >= month_start_str and info["event_count"] > 0
        )
        avg_daily = round(month_net / days_with_data, 1) if days_with_data > 0 else 0.0

        return WritingStatsOverview(
            project_id=project_id,
            generated_at=datetime.now(timezone.utc),
            range_days=days,
            total_words=total_words,
            target_words=target_words,
            progress_percent=progress_percent,
            today_net_words=today_net,
            week_net_words=week_net,
            month_net_words=month_net,
            current_streak_days=current_streak,
            longest_streak_days=longest_streak,
            average_daily_words_30d=avg_daily,
            estimated_today_minutes=today_minutes,
            estimated_words_per_hour_today=today_wph,
            daily=daily_points,
            hourly=hourly_points,
            volume_breakdown=volume_breakdown,
            chapter_rankings=chapter_rankings,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_streaks(event_dates: list[str], today: date) -> tuple[int, int]:
        if not event_dates:
            return 0, 0

        date_set = {date.fromisoformat(date_str) for date_str in event_dates}
        sorted_dates = sorted(date_set)

        # Longest streak overall
        longest = 1
        current_run = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                current_run += 1
                longest = max(longest, current_run)
            else:
                current_run = 1

        # Current streak: count back from today
        current = 0
        check_date = today
        while check_date in date_set:
            current += 1
            check_date -= timedelta(days=1)

        return current, longest

    @staticmethod
    def _estimate_active_minutes(events: list[WritingStatEvent]) -> int:
        if not events:
            return 0

        if len(events) == 1:
            return ISOLATED_EVENT_MINUTES

        sorted_events = sorted(events, key=lambda event: event.occurred_at)
        total_minutes = 0.0
        session_start = sorted_events[0].occurred_at
        session_end = session_start

        for i in range(1, len(sorted_events)):
            event_time = sorted_events[i].occurred_at
            gap_seconds = (event_time - session_end).total_seconds()
            gap_minutes = gap_seconds / 60

            if gap_minutes <= ACTIVE_SESSION_GAP_MINUTES:
                session_end = event_time
            else:
                session_duration = (session_end - session_start).total_seconds() / 60
                total_minutes += max(session_duration, ISOLATED_EVENT_MINUTES)
                session_start = event_time
                session_end = event_time

        last_duration = (session_end - session_start).total_seconds() / 60
        total_minutes += max(last_duration, ISOLATED_EVENT_MINUTES)

        return max(round(total_minutes), 1)
