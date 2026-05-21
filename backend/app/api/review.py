from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.review import (
    ProhibitedTermCreate,
    ProhibitedTermRead,
    ProhibitedTermUpdate,
    ReviewCheckRequest,
    ReviewCheckResponse,
)
from app.services.review_service import ReviewNotFoundError, ReviewService


router = APIRouter(tags=["review"])


def get_review_service(db: Session = Depends(get_db)) -> ReviewService:
    return ReviewService(db)


@router.get("/api/review/prohibited-terms", response_model=list[ProhibitedTermRead])
def list_prohibited_terms(service: ReviewService = Depends(get_review_service)):
    return service.list_prohibited_terms()


@router.post(
    "/api/review/prohibited-terms",
    response_model=ProhibitedTermRead,
    status_code=status.HTTP_201_CREATED,
)
def create_prohibited_term(
    data: ProhibitedTermCreate,
    service: ReviewService = Depends(get_review_service),
):
    return service.create_prohibited_term(data)


@router.patch("/api/review/prohibited-terms/{term_id}", response_model=ProhibitedTermRead)
def update_prohibited_term(
    term_id: str,
    data: ProhibitedTermUpdate,
    service: ReviewService = Depends(get_review_service),
):
    try:
        return service.update_prohibited_term(term_id, data)
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Prohibited term not found") from exc


@router.delete("/api/review/prohibited-terms/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prohibited_term(
    term_id: str,
    service: ReviewService = Depends(get_review_service),
):
    try:
        service.delete_prohibited_term(term_id)
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Prohibited term not found") from exc


@router.post("/api/projects/{project_id}/review/check", response_model=ReviewCheckResponse)
def run_project_review_check(
    project_id: str,
    data: ReviewCheckRequest,
    service: ReviewService = Depends(get_review_service),
):
    try:
        return service.run_check(project_id, data)
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Review target not found") from exc


@router.get("/api/projects/{project_id}/review/results", response_model=ReviewCheckResponse)
def list_project_review_results(
    project_id: str,
    service: ReviewService = Depends(get_review_service),
):
    try:
        return service.list_results(project_id)
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
