import base64
import json

from app.config import settings


def _fernet():
    from cryptography.fernet import Fernet

    raw = settings.gateway_secrets_key or ""
    if not raw:
        return None
    if len(raw) == 44 and raw.endswith("="):
        key = raw.encode("ascii")
    else:
        key = base64.urlsafe_b64encode(raw.encode("utf-8")[:32].ljust(32, b"\0"))
    return Fernet(key)


def encrypt_secrets(payload: dict) -> bytes:
    f = _fernet()
    if not f:
        raise ValueError("GATEWAY_SECRETS_KEY not configured")
    return f.encrypt(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def decrypt_secrets(ciphertext: bytes) -> dict:
    f = _fernet()
    if not f:
        raise ValueError("GATEWAY_SECRETS_KEY not configured")
    return json.loads(f.decrypt(ciphertext).decode("utf-8"))
