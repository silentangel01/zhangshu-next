from datetime import datetime
from typing import Literal

from pydantic import BaseModel


ALLOWED_RANGE_DAYS = (30, 90, 365)
RangeDays = Literal[30, 90, 365]


class WritingStatsDailyPoint(BaseModel):
    date: str
    net_words: int
    added_words: int
    deleted_words: int
    event_count: int
    active_minutes_estimated: int


class WritingStatsHourlyPoint(BaseModel):
    hour: int
    net_words: int
    event_count: int


class WritingStatsVolumeBreakdownItem(BaseModel):
    volume_id: str | None
    title: str
    total_words: int
    chapter_count: int


class WritingStatsChapterRankingItem(BaseModel):
    chapter_id: str
    title: str
    volume_id: str | None
    volume_title: str
    total_words: int
    delta_words_7d: int
    updated_at: datetime


class WritingStatsOverview(BaseModel):
    project_id: str
    generated_at: datetime
    range_days: int
    total_words: int
    target_words: int | None
    progress_percent: float | None
    today_net_words: int
    week_net_words: int
    month_net_words: int
    current_streak_days: int
    longest_streak_days: int
    average_daily_words_30d: float
    estimated_today_minutes: int
    estimated_words_per_hour_today: float
    daily: list[WritingStatsDailyPoint]
    hourly: list[WritingStatsHourlyPoint]
    volume_breakdown: list[WritingStatsVolumeBreakdownItem]
    chapter_rankings: list[WritingStatsChapterRankingItem]
    warnings: list[str]
