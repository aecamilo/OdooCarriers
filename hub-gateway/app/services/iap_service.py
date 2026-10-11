import uuid
from typing import Any

from app.config import settings
from app.db import db_cursor
from app.services.ledger_service import add_iap_credits, iap_credit_balance
from app.services.token_service import hash_iap_account_token


def _provision_lazy():
    from app.services.provision_service import provision_account
    return provision_account


def _account_by_iap_token(account_token: str) -> int | None:
    iap_hash = hash_iap_account_token(account_token)
    with db_cursor() as (_, cur):
        cur.execute(
            "SELECT id, status FROM accounts WHERE iap_account_token_hash = %s",
            (iap_hash,),
        )
        row = cur.fetchone()
    if not row or row["status"] != "active":
        return None
    return int(row["id"])




def handle_iap_jsonrpc(payload: dict) -> dict:
    method = payload.get("method") or ""
    params = payload.get("params") or {}
    req_id = payload.get("id")

    def wrap(result=None, error=None):
        out = {"jsonrpc": "2.0", "id": req_id}
        if error:
            out["error"] = error
        else:
            out["result"] = result
        return out

    if method == "iap.account_token":
        account_token = params.get("account_token") or ""
        account_id = _account_by_iap_token(account_token)
        if not account_id:
            _, prov = _provision_lazy()(account_token, plan_code="free")
            account_id = prov.get("account_id")
        balance = iap_credit_balance(account_id)
        return wrap({"status": "ok", "credit_left": balance})

    if method in ("iap.charge", "charge"):
        account_token = params.get("account_token") or ""
        credit = float(params.get("credit") or settings.credit_per_label)
        tx_id = params.get("transaction_id") or str(uuid.uuid4())
        account_id = _account_by_iap_token(account_token)
        if not account_id:
            return wrap(error={"code": 404, "message": "Unknown IAP account"})

        with db_cursor() as (_, cur):
            cur.execute(
                "SELECT id, status FROM iap_transactions WHERE iap_transaction_id = %s",
                (tx_id,),
            )
            existing = cur.fetchone()
            if existing and existing["status"] == "captured":
                return wrap({"status": "ok", "credit_left": iap_credit_balance(account_id)})

        balance = iap_credit_balance(account_id)
        if balance < credit:
            return wrap(error={"code": 402, "message": "Insufficient credit"})

        with db_cursor() as (_, cur):
            cur.execute(
                """
                INSERT INTO iap_transactions (id, account_id, iap_transaction_id, credit_amount, status)
                VALUES (%s, %s, %s, %s, 'captured')
                ON DUPLICATE KEY UPDATE status = 'captured'
                """,
                (str(uuid.uuid4()), account_id, tx_id, credit),
            )
        add_iap_credits(account_id, -credit, "label_charge", tx_id)
        return wrap({"status": "ok", "credit_left": iap_credit_balance(account_id)})

    if method in ("iap.credit", "credit"):
        account_token = params.get("account_token") or ""
        credit = float(params.get("credit") or 0)
        account_id = _account_by_iap_token(account_token)
        if not account_id:
            _, prov = _provision_lazy()(account_token, plan_code="free")
            account_id = prov.get("account_id")
        add_iap_credits(account_id, credit, "iap_purchase", params.get("transaction_id"))
        return wrap({"status": "ok", "credit_left": iap_credit_balance(account_id)})

    return wrap(error={"code": 400, "message": f"Unknown method {method}"})
