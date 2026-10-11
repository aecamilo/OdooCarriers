from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.errors import error_response
from app.services.connection_service import test_dpd_connection

router = APIRouter(prefix="/api/v1/dpd", tags=["dpd"])


class DpdConnectionTestRequest(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)
    environment: str = "stage"
    credentials: dict | None = None


@router.post("/connections/test")
async def post_dpd_connections_test(body: DpdConnectionTestRequest, request: Request):
    account_id = getattr(request.state, "account_id", None)
    if not account_id:
        return error_response(401, "invalid_token")
    status, result = test_dpd_connection(
        account_id,
        body.country_code,
        body.environment,
        body.credentials,
    )
    if result.get("success"):
        return result
    return error_response(
        status,
        result.get("error_code", "internal_error"),
        result.get("error_detail", ""),
    )
