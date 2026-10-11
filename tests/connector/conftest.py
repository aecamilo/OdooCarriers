"""Load shipping_hub_client without importing the full Odoo addon package."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

CONNECTOR_ROOT = Path(__file__).resolve().parents[2] / "shipping_hub_connector"
CLIENT_PATH = CONNECTOR_ROOT / "models" / "shipping_hub_client.py"
MODULE_NAME = "shipping_hub_client_under_test"


class UserError(Exception):
    pass


def _mock_odoo() -> None:
    odoo = ModuleType("odoo")
    odoo._ = lambda s: s
    exceptions = ModuleType("odoo.exceptions")
    exceptions.UserError = UserError
    sys.modules["odoo"] = odoo
    sys.modules["odoo.exceptions"] = exceptions


_mock_odoo()


def load_hub_client_module():
    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]
    spec = importlib.util.spec_from_file_location(MODULE_NAME, CLIENT_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[MODULE_NAME] = mod
    spec.loader.exec_module(mod)
    return mod


hub_client = load_hub_client_module()


@pytest.fixture
def mod():
    return hub_client
