import os

import pymysql
from fastapi import FastAPI

from app.config import settings
from app.middleware.auth_hmac import HmacAuthMiddleware
from app.routes import accounts, dpd_connections, iap_service, meta, odoo_api

app = FastAPI(title=settings.app_name)
app.add_middleware(HmacAuthMiddleware)
app.include_router(meta.router)
app.include_router(odoo_api.router)
app.include_router(dpd_connections.router)
app.include_router(accounts.router)
app.include_router(iap_service.router)


def _db_ping() -> bool:
    if not settings.db_password:
        return False
    try:
        conn = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_username,
            password=settings.db_password,
            database=settings.db_database,
            connect_timeout=3,
        )
        conn.close()
        return True
    except pymysql.MySQLError:
        return False


@app.get("/healthz")
def healthz():
    db_ok = _db_ping()
    body = {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
    }
    if settings.app_debug:
        body["simulator"] = settings.gateway_carrier_simulator
    return body


@app.get("/")
def root():
    return {
        "service": settings.app_name,
        "health": "/healthz",
        "public_url": settings.app_public_url or os.getenv("APP_PUBLIC_URL", ""),
    }
