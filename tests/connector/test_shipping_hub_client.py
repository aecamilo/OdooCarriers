from unittest.mock import MagicMock, patch

import pytest

from conftest import UserError, hub_client as mod


@pytest.fixture
def client():
    return mod.ShippingHubClient("https://hub.example", "test-api-token-0123456789ab")


def test_sign_matches_gateway_canonical(client):
    body = b"{\"a\":1}"
    sig = client._sign("POST", "/api/v1/shipments/labels", body, "1700000000", "nonce-1")
    assert sig.startswith("sha256=")
    assert len(sig) == 7 + 64


def test_request_rejects_missing_url():
    c = mod.ShippingHubClient("", "test-api-token-0123456789ab")
    with pytest.raises(UserError, match="URL"):
        c._request("POST", "/api/v1/shipments/labels", {})


def test_request_rejects_short_token(client):
    c = mod.ShippingHubClient("https://hub.example", "short")
    with pytest.raises(UserError, match="token"):
        c._request("POST", "/api/v1/shipments/labels", {})


def test_parse_response_success():
    resp = MagicMock()
    resp.ok = True
    resp.content = b"{\"success\": true, \"tracking_number\": \"T1\"}"
    resp.json.return_value = {"success": True, "tracking_number": "T1"}
    out = mod.ShippingHubClient("", "")._parse_response(resp)
    assert out["success"] is True


def test_parse_response_maps_error_code():
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 429
    resp.content = b"{\"success\": false, \"error_code\": \"rate_limit_exceeded\"}"
    resp.json.return_value = {"success": False, "error_code": "rate_limit_exceeded"}
    out = mod.ShippingHubClient("", "")._parse_response(resp)
    assert out["success"] is False
    assert out["error_code"] == "rate_limit_exceeded"
    assert "minute" in out["error_message"].lower()


def test_create_label_calls_post(client):
    with patch.object(client, "_request", return_value={"success": True}) as req:
        body = {"reference": "SO1"}
        assert client.create_label(body) == {"success": True}
        req.assert_called_once_with("POST", mod.LABELS_PATH, body)


def test_test_connection_health_fail(client):
    with patch(f"{mod.__name__}.requests.get") as get:
        get.side_effect = mod.requests.exceptions.ConnectionError("down")
        with pytest.raises(UserError, match="health"):
            client.test_connection()


def test_test_connection_invalid_payload_ok(client):
    health = MagicMock()
    health.raise_for_status = MagicMock()
    with patch(f"{mod.__name__}.requests.get", return_value=health):
        with patch.object(
            client,
            "_request",
            return_value={"success": False, "error_code": "invalid_payload", "http_status": 400},
        ):
            assert client.test_connection() is True


def test_humanize_hub_error():
    assert mod.humanize_hub_error({"success": False, "error_message": "x"}) == "x"
    assert mod.humanize_hub_error({"success": True}) == ""
