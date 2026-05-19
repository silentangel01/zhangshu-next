from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.volume import Volume
from app.repositories.project_repo import ProjectRepository
from app.repositories.volume_repo import VolumeRepository
from app.schemas.volume import VolumeCreate, VolumeUpdate


class VolumeNotFoundError(Exception):
    pass


class VolumeProjectNotFoundError(Exception):
    pass


class VolumeService:
    def __init__(self, db: Session):
        self.project_repo = ProjectRepository(db)
        self.volume_repo = VolumeRepository(db)

    def list_project_volumes(self, project_id: str) -> list[Volume]:
        self._ensure_project_exists(project_id)
        return self.volume_repo.list_active_by_project(project_id)

    def create_volume(self, project_id: str, data: VolumeCreate) -> Volume:
        self._ensure_project_exists(project_id)
        volume = Volume(
            id=str(uuid4()),
            project_id=project_id,
            title=data.title,
            order_index=data.order_index,
        )
        return self.volume_repo.create(volume)

    def update_volume(self, volume_id: str, data: VolumeUpdate) -> Volume:
        volume = self.get_volume(volume_id)
        values = data.model_dump(exclude_unset=True)
        return self.volume_repo.update(volume, values)

    def delete_volume(self, volume_id: str) -> Volume:
        volume = self.get_volume(volume_id)
        return self.volume_repo.soft_delete(volume)

    def get_volume(self, volume_id: str) -> Volume:
        volume = self.volume_repo.get_active(volume_id)
        if volume is None:
            raise VolumeNotFoundError
        return volume

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise VolumeProjectNotFoundError
