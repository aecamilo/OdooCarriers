import uuid
from typing import Optional

from app.db import db_cursor
from app.services.quota_service import ensure_subscription_row
from app.services.ledger_service import add_iap_credits
from app.services.token_service import (
    generate_api_token,
    hash_iap_account_token,
    store_api_token,
)


def provision_account(
    iap_account_token: str,
    contact_email: Optional[str] = None,
    plan_code: str = "free",
) -> tuple[int, dict]:
    if not iap_account_token or len(iap_account_token) < 8:
        return 400, {"success": False, "error_code": "invalid_payload"}

    if plan_code not in ("free", "starter", "pro", "enterprise"):
        plan_code = "free"

    iap_hash = hash_iap_account_token(iap_account_token)

    with db_cursor() as (_, cur):
        cur.execute(
            "SELECT id FROM accounts WHERE iap_account_token_hash = %s",
            (iap_hash,),
        )
        existing = cur.fetchone()
        if existing:
            account_id = int(existing["id"])
            api_token = generate_api_token()
            store_api_token(account_id, api_token)
            return 200, {
                "success": True,
                "account_id": account_id,
                "api_token": api_token,
                "message": "Token reissued for existing IAP account.",
            }

        cur.execute(
            """
            INSERT INTO accounts (status, contact_email, iap_account_token_hash)
            VALUES ('active', %s, %s)
            """,
            (contact_email, iap_hash),
        )
        account_id = int(cur.lastrowid)

    ensure_subscription_row(account_id, plan_code)
    api_token = generate_api_token()
    store_api_token(account_id, api_token)
    add_iap_credits(account_id, 50.0, "provision_welcome", None)
    return 201, {
        "success": True,
        "account_id": account_id,
        "api_token": api_token,
    }
