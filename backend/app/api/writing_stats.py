from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.writing_stats import ALLOWED_RANGE_DAYS, WritingStatsOverview
from app.services.writing_stats_service import (
    WritingStatsProjectNotFoundError,
    WritingStatsService,
)


router = APIRouter(tags=["writing-stats"])


def get_writing_stats_service(db: Session = Depends(get_db)) -> WritingStatsService:
    return WritingStatsService(db)


@router.get(
    "/api/projects/{project_id}/writing-stats/overview",
    response_model=WritingStatsOverview,
)
def get_writing_stats_overview(
    project_id: str,
    days: int = Query(default=90),
    service: WritingStatsService = Depends(get_writing_stats_service),
) -> WritingStatsOverview:
    if days not in ALLOWED_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"days 参数必须为 {list(ALLOWED_RANGE_DAYS)} 之一。",
        )
    try:
        return service.get_overview(project_id, days=days)
    except WritingStatsProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在。",
        )
