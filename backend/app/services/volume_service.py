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
        self.db = db
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
        created = self.volume_repo.create(volume)
        self._mark_dirty(project_id, created.id, "upsert")
        return created

    def update_volume(self, volume_id: str, data: VolumeUpdate) -> Volume:
        volume = self.get_volume(volume_id)
        values = data.model_dump(exclude_unset=True)
        updated = self.volume_repo.update(volume, values)
        self._mark_dirty(volume.project_id, volume_id, "upsert")
        return updated

    def delete_volume(self, volume_id: str) -> Volume:
        volume = self.get_volume(volume_id)
        deleted = self.volume_repo.soft_delete(volume)
        self._mark_dirty(volume.project_id, volume_id, "delete")
        return deleted

    def get_volume(self, volume_id: str) -> Volume:
        volume = self.volume_repo.get_active(volume_id)
        if volume is None:
            raise VolumeNotFoundError
        return volume

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise VolumeProjectNotFoundError

    def _mark_dirty(self, project_id: str, entity_id: str, action: str) -> None:
        """Mark the volume as dirty for cloud sync (best-effort, never raises)."""
        try:
            from app.services.sync_dirty_service import SyncDirtyService

            SyncDirtyService(self.db).mark_dirty(project_id, "volumes", entity_id, action)
        except Exception:
            pass
