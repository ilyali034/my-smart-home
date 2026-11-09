from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DeviceCreateDto(BaseModel):
    device_name: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=50)
    room: Optional[str] = Field(default=None, max_length=100)


class DeviceUpdateDto(BaseModel):
    device_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    type: Optional[str] = Field(default=None, min_length=1, max_length=50)
    room: Optional[str] = Field(default=None, max_length=100)
    is_on: Optional[bool] = None


class DeviceStateDto(BaseModel):
    is_on: bool


class DeviceDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_name: str
    type: str
    room: Optional[str] = None
    is_on: bool
    created_at: datetime
    updated_at: datetime

