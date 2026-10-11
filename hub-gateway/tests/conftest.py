"""Pytest fixtures for hub-gateway (no MySQL required for unit/API smoke tests)."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_DEBUG", "true")
os.environ.setdefault("GATEWAY_CARRIER_SIMULATOR", "true")
os.environ.setdefault("SC_HMAC_REQUIRED", "true")
os.environ.setdefault("DB_PASSWORD", "")
os.environ.setdefault("REQUIRE_ODOO_DATABASE_UUID", "false")

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
