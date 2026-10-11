from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["meta"])

API_VERSION = "1.0.0-dpd-mvp"


@router.get("/version")
def api_version():
    return {
        "success": True,
        "api_version": API_VERSION,
        "service": settings.app_name,
        "schema_version": "1.0",
        "target": "carrier_gateway",
        "auth": {
            "iap_service_name": settings.iap_service_name,
            "database_uuid_header": "X-Odoo-Database-Uuid",
            "transition_bearer_token": True,
        },
    }
