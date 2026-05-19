from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VolumeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    order_index: int = Field(default=0, ge=0)

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class VolumeCreate(VolumeBase):
    pass


class VolumeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    order_index: int | None = Field(default=None, ge=0)

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value

        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class VolumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    order_index: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
