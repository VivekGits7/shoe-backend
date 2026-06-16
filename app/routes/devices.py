from fastapi import APIRouter
from pydantic import BaseModel

from app.devices import DEVICES

router = APIRouter(prefix="/api/devices", tags=["devices"])


class DeviceOption(BaseModel):
    value: str
    label: str


@router.get("", response_model=list[DeviceOption])
def list_devices():
    return DEVICES
