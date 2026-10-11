import hashlib
import hmac
import time
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.errors import error_response
from app.services.nonce_service import register_nonce
from app.services.account_uuid_service import validate_account_database_uuid
from app.services.token_service import resolve_account_by_token


class AuthContext:
    account_id: Optional[int] = None


def verify_hmac(method: str, path: str, body: bytes, token: str, timestamp: str, nonce: str, signature: str) -> bool:
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = f"{method}\n{path}\n\n{timestamp}\n{nonce}\n{body_hash}\n"
    digest = hmac.new(
        token.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature)


class HmacAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        if not path.startswith("/api/v1/"):
            return await call_next(request)

        if path in ("/api/v1/accounts/provision", "/api/v1/version"):
            body = await request.body()

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request._receive = receive
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return error_response(401, "invalid_token", "Missing Bearer token")
        token = auth[7:].strip()
        account_id = resolve_account_by_token(token)
        if not account_id:
            return error_response(401, "invalid_token")

        body = await request.body()

        if settings.sc_hmac_required:
            ts = request.headers.get("X-SC-Timestamp", "")
            nonce = request.headers.get("X-SC-Nonce", "")
            sig = request.headers.get("X-SC-Signature", "")
            if not ts or not nonce or not sig:
                return error_response(401, "invalid_signature")
            try:
                ts_int = int(ts)
            except ValueError:
                return error_response(401, "timestamp_out_of_range")
            now = int(time.time())
            if abs(now - ts_int) > settings.sc_hmac_max_skew_sec:
                return error_response(401, "timestamp_out_of_range")
            if not verify_hmac(request.method, path, body, token, ts, nonce, sig):
                return error_response(401, "invalid_signature")
            if not register_nonce(nonce, account_id):
                return error_response(401, "nonce_reused")


        if settings.require_odoo_database_uuid:
            db_uuid = request.headers.get("X-Odoo-Database-Uuid", "")
            ok, err_code = validate_account_database_uuid(account_id, db_uuid)
            if not ok:
                return error_response(401, err_code)

        request.state.account_id = account_id
        request.state.raw_body = body

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive
        return await call_next(request)
