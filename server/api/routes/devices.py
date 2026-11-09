from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from server.api.routes.auth import get_current_user
from server.engine.database.device_repository import DeviceRepository
from server.shared.device_dto import DeviceCreateDto, DeviceDto, DeviceStateDto, DeviceUpdateDto


router = APIRouter(prefix="/api/devices", tags=["devices"])


def get_device_repository(request: Request) -> DeviceRepository:
    return request.app.state.device_repository


@router.get("", response_model=list[DeviceDto])
async def list_devices(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    devices: Annotated[DeviceRepository, Depends(get_device_repository)],
    room: Optional[str] = Query(default=None, max_length=100),
    device_type: Optional[str] = Query(default=None, alias="type", max_length=50),
) -> list[DeviceDto]:
    rows = await devices.list_devices(user["id"], room=room, device_type=device_type)
    return [DeviceDto(**row) for row in rows]


@router.post("", response_model=DeviceDto, status_code=status.HTTP_201_CREATED)
async def create_device(
    payload: DeviceCreateDto,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    devices: Annotated[DeviceRepository, Depends(get_device_repository)],
) -> DeviceDto:
    if not payload.device_name.strip() or not payload.type.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name and type cannot be blank")
    row = await devices.add_device(user["id"], payload.device_name, payload.type, payload.room)
    return DeviceDto(**row)


@router.get("/{device_id}", response_model=DeviceDto)
async def get_device(
    device_id: int,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    devices: Annotated[DeviceRepository, Depends(get_device_repository)],
) -> DeviceDto:
    row = await devices.get_device(device_id, user["id"])
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceDto(**row)


@router.patch("/{device_id}", response_model=DeviceDto)
async def update_device(
    device_id: int,
    payload: DeviceUpdateDto,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    devices: Annotated[DeviceRepository, Depends(get_device_repository)],
) -> DeviceDto:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one field is required")
    for field in ("device_name", "type"):
        if field in changes and not changes[field].strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field} cannot be blank")
    if "room" in changes and changes["room"] is not None:
        changes["room"] = changes["room"].strip()
    row = await devices.update_device(device_id, user["id"], changes)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceDto(**row)


@router.patch("/{device_id}/state", response_model=DeviceDto)
async def set_device_state(
    device_id: int,
    payload: DeviceStateDto,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    devices: Annotated[DeviceRepository, Depends(get_device_repository)],
) -> DeviceDto:
    row = await devices.update_device(device_id, user["id"], {"is_on": payload.is_on})
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceDto(**row)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: int,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    devices: Annotated[DeviceRepository, Depends(get_device_repository)],
) -> None:
    if not await devices.delete_device(device_id, user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
