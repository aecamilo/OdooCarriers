import hashlib
import hmac
import json
import time
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _signed_headers(method: str, path: str, body_dict, token: str) -> dict:
    body_bytes = json.dumps(body_dict, separators=(",", ":")).encode("utf-8")
    ts = str(int(time.time()))
    nonce = str(uuid.uuid4())
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    canonical = f"{method}\n{path}\n\n{ts}\n{nonce}\n{body_hash}\n"
    digest = hmac.new(
        token.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-SC-Timestamp": ts,
        "X-SC-Nonce": nonce,
        "X-SC-Signature": f"sha256={digest}",
    }


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(app)


def test_healthz_returns_json(api_client: TestClient):
    r = api_client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "database" in data


def test_root(api_client: TestClient):
    r = api_client.get("/")
    assert r.status_code == 200
    assert r.json().get("health") == "/healthz"


def test_labels_without_bearer_401(api_client: TestClient):
    r = api_client.post("/api/v1/shipments/labels", json={})
    assert r.status_code == 401
    assert r.json().get("error_code") == "invalid_token"


def test_labels_invalid_token_401(api_client: TestClient):
    with patch("app.middleware.auth_hmac.resolve_account_by_token", return_value=None):
        token = "invalid-but-long-enough-token"
        headers = _signed_headers("POST", "/api/v1/shipments/labels", {}, token)
        r = api_client.post("/api/v1/shipments/labels", headers=headers, content=b"{}")
    assert r.status_code == 401


def test_labels_empty_body_invalid_payload(api_client: TestClient):
    token = "valid-test-token-0123456789ab"
    with patch("app.middleware.auth_hmac.resolve_account_by_token", return_value=1):
        with patch("app.middleware.auth_hmac.register_nonce", return_value=True):
            headers = _signed_headers("POST", "/api/v1/shipments/labels", {}, token)
            r = api_client.post("/api/v1/shipments/labels", headers=headers, content=b"{}")
    assert r.status_code == 400
    assert r.json().get("error_code") == "invalid_payload"


def test_provision_requires_key_when_not_debug(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "app_debug", False)
    monkeypatch.setattr(settings, "iap_service_key", "secret-provision-key")
    client = TestClient(app)
    r = client.post(
        "/api/v1/accounts/provision",
        json={"iap_account_token": "iap-test-token-12345678"},
    )
    assert r.status_code == 401


def test_provision_wrong_key(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "iap_service_key", "secret-provision-key")
    client = TestClient(app)
    r = client.post(
        "/api/v1/accounts/provision",
        json={"iap_account_token": "iap-test-token-12345678"},
        headers={"X-OdooCarriers-Provision-Key": "wrong"},
    )
    assert r.status_code == 401
