from fastapi import APIRouter, Header, Request

from app.config import settings
from app.errors import error_response
from app.services.iap_service import handle_iap_jsonrpc

router = APIRouter(tags=["iap"])


@router.post("/iap/1/{service_name}")
async def iap_service_endpoint(
    service_name: str,
    request: Request,
    authorization: str = Header(default=""),
):
    if service_name != settings.iap_service_name:
        return error_response(404, "internal_error", "Unknown IAP service")

    expected = f"Bearer {settings.iap_service_key}" if settings.iap_service_key else ""
    if settings.iap_service_key and authorization != expected:
        return error_response(401, "invalid_token", "Invalid IAP service authorization")

    try:
        payload = await request.json()
    except Exception:
        return error_response(400, "invalid_payload")

    result = handle_iap_jsonrpc(payload)
    return result


@router.post("/iap/1/{service_name}/charge")
async def iap_charge_alias(service_name: str, request: Request, authorization: str = Header(default="")):
    return await iap_service_endpoint(service_name, request, authorization)
