import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.review import (
    ProhibitedTermCreate,
    ProhibitedTermImportReport,
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


@router.get("/api/review/prohibited-terms/export")
def export_prohibited_terms(service: ReviewService = Depends(get_review_service)):
    payload = service.export_prohibited_terms()
    content = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="zhangshu_prohibited_terms.json"'},
    )


@router.post("/api/review/prohibited-terms/import", response_model=ProhibitedTermImportReport)
async def import_prohibited_terms(
    file: UploadFile = File(...),
    service: ReviewService = Depends(get_review_service),
):
    filename = file.filename or ""
    if file.content_type not in {None, "", "application/json", "text/json"} and not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="请上传 JSON 文件。")

    raw_content = await file.read()
    if len(raw_content) > 1024 * 1024:
        raise HTTPException(status_code=400, detail="词库文件过大。")

    try:
        payload = json.loads(raw_content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="词库导入失败，请检查文件格式。") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="词库导入失败，请检查文件格式。")

    return service.import_prohibited_terms(payload)


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
