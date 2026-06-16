from fastapi import APIRouter, Request

from devices import DEVICES
from limiter import limiter
from schema.devices.devices import DeviceListResponse
from schema.response import COMMON_ERROR_RESPONSES

router = APIRouter(prefix="/api/devices", tags=["Devices"])


@router.get(
    "",
    response_model=DeviceListResponse,
    summary="List available device types",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {"model": DeviceListResponse, "description": "List of supported device types"},
    },
)
@limiter.limit("60/minute")
async def list_devices(request: Request) -> DeviceListResponse:
    """
    Return all supported device types.

    - Returns static list: `shoe`, `sandal`
    """
    return DeviceListResponse(success=True, data=DEVICES)
