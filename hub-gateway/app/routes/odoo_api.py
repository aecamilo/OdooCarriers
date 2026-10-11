import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.errors import error_response
from app.services.label_service import create_label

router = APIRouter(prefix="/api/v1", tags=["odoo"])


@router.post("/shipments/labels")
async def post_shipments_labels(request: Request):
    account_id = getattr(request.state, "account_id", None)
    if not account_id:
        return error_response(401, "invalid_token")
    raw = getattr(request.state, "raw_body", b"")
    try:
        data = json.loads(raw.decode("utf-8") if raw else "{}")
    except json.JSONDecodeError:
        return error_response(400, "invalid_payload")
    status, body = create_label(account_id, data)
    if body.get("success"):
        return JSONResponse(status_code=status, content=body)
    return error_response(status, body.get("error_code", "internal_error"), body.get("error_detail", ""))
