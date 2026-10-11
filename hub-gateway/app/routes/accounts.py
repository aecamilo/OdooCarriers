from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.errors import error_response
from app.schemas.provision import ProvisionRequest
from app.services.provision_service import provision_account

router = APIRouter(prefix="/api/v1", tags=["accounts"])


@router.post("/accounts/provision")
async def post_accounts_provision(body: ProvisionRequest, request: Request):
    service_key = request.headers.get("X-OdooCarriers-Provision-Key", "")
    if settings.iap_service_key:
        if service_key != settings.iap_service_key:
            return error_response(401, "invalid_token", "Provision key required")
    elif not settings.app_debug:
        return error_response(401, "invalid_token", "Provision key required")

    status, result = provision_account(
        body.iap_account_token,
        contact_email=body.contact_email,
        plan_code=body.plan_code or "free",
    )
    if not result.get("success"):
        return error_response(status, result.get("error_code", "internal_error"))
    return JSONResponse(status_code=status, content=result)
