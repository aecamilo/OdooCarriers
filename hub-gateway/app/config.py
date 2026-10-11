from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_GATEWAY_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "OdooCarriers"
    app_debug: bool = False
    app_public_url: str = ""

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_database: str = "odoocarriers"
    db_username: str = "saas"
    db_password: str = ""

    saas_key_pepper: str = ""
    iap_service_key: str = ""
    sc_hmac_max_skew_sec: int = 300
    sc_hmac_required: bool = True

    gateway_carrier_simulator: bool = False
    plan_catalog_path: str = str(_GATEWAY_ROOT / "data" / "plan_catalog.json")

    gateway_secrets_key: str = ""
    require_odoo_database_uuid: bool = True

    iap_service_name: str = "odoocarriers_shipping_labels"
    credit_per_label: float = 1.0


settings = Settings()
