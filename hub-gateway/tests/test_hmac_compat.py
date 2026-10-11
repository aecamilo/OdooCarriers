"""HMAC signing must match between Odoo ShippingHubClient and gateway middleware."""

import hashlib
import hmac
import json
import uuid

from app.middleware.auth_hmac import verify_hmac


def _odoo_style_sign(method, path, body_dict, token, timestamp, nonce):
    if body_dict is not None:
        body_bytes = json.dumps(
            body_dict, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    else:
        body_bytes = b""
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    canonical = f"{method}\n{path}\n\n{timestamp}\n{nonce}\n{body_hash}\n"
    digest = hmac.new(
        token.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}", body_bytes


def test_odoo_and_gateway_signatures_match():
    token = "test-api-token-0123456789abcdef"
    path = "/api/v1/shipments/labels"
    body = {"schema_version": "1.0", "operation": "create_shipment"}
    ts = "1700000000"
    nonce = str(uuid.uuid4())

    signature, body_bytes = _odoo_style_sign("POST", path, body, token, ts, nonce)
    assert verify_hmac("POST", path, body_bytes, token, ts, nonce, signature)


def test_wrong_signature_rejected():
    token = "test-api-token-0123456789abcdef"
    path = "/api/v1/shipments/labels"
    body_bytes = b"{}"
    ts = "1700000000"
    nonce = "n1"
    assert not verify_hmac("POST", path, body_bytes, token, ts, nonce, "sha256=deadbeef")
