import uuid
from typing import Any, Optional

from app.config import settings
from app.db import db_cursor
from app.services.secrets_service import encrypt_secrets


def test_dpd_connection(
    account_id: int,
    country_code: str,
    environment: str,
    credentials: Optional[dict[str, Any]] = None,
) -> tuple[int, dict]:
    country_code = (country_code or "").upper()[:2]
    if country_code not in ("DE", "FR", "NL", "BE", "UK"):
        return 400, {
            "success": False,
            "error_code": "invalid_payload",
            "error_detail": "Unsupported country_code for DPD test.",
        }
    if environment not in ("stage", "live"):
        environment = "stage"

    if settings.gateway_carrier_simulator or settings.app_debug:
        return 200, {
            "success": True,
            "country_code": country_code,
            "environment": environment,
            "depot_id": "SIM-DEPOT",
            "permissions": ["label", "rate"],
            "message": "DPD connection test OK (simulator).",
        }

    if not credentials:
        return 400, {
            "success": False,
            "error_code": "carrier_credentials_missing",
        }

    return 502, {
        "success": False,
        "error_code": "carrier_error",
        "error_detail": "DPD adapter not implemented for this country yet.",
    }


def upsert_connection_with_secrets(
    account_id: int,
    external_ref: str,
    country_code: str,
    environment: str,
    credentials: dict,
    company_name: str = "",
    warehouse_ref: str = "",
) -> str:
    conn_id = str(uuid.uuid4())
    ciphertext = encrypt_secrets(credentials)
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT id FROM connections
            WHERE account_id = %s AND external_ref = %s
            """,
            (account_id, external_ref),
        )
        existing = cur.fetchone()
        if existing:
            conn_id = existing["id"]
            cur.execute(
                """
                UPDATE connections SET country_code = %s, environment = %s,
                    company_name = %s, warehouse_ref = %s, updated_at = UTC_TIMESTAMP(3)
                WHERE id = %s
                """,
                (country_code, environment, company_name, warehouse_ref, conn_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO connections (
                    id, account_id, external_ref, company_name, warehouse_ref,
                    country_code, environment, carrier_code, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'dpd', 'active')
                """,
                (
                    conn_id,
                    account_id,
                    external_ref,
                    company_name or None,
                    warehouse_ref or None,
                    country_code,
                    environment,
                ),
            )
        cur.execute(
            """
            INSERT INTO connection_secrets (connection_id, secrets_ciphertext, secrets_key_version)
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE secrets_ciphertext = VALUES(secrets_ciphertext),
                updated_at = UTC_TIMESTAMP(3)
            """,
            (conn_id, ciphertext),
        )
    return conn_id
