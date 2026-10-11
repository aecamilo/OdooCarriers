from datetime import datetime, timezone
from typing import Any, Optional

from app.db import db_cursor
from app.services.plan_catalog import get_plan


def _current_yyyymm() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m")


def get_subscription(account_id: int) -> Optional[dict]:
    with db_cursor() as (_, cur):
        cur.execute(
            "SELECT * FROM subscriptions WHERE account_id = %s",
            (account_id,),
        )
        return cur.fetchone()


def ensure_subscription_row(account_id: int, plan_code: str = "free") -> dict:
    yyyymm = _current_yyyymm()
    with db_cursor() as (_, cur):
        cur.execute(
            "SELECT * FROM subscriptions WHERE account_id = %s FOR UPDATE",
            (account_id,),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                """
                INSERT INTO subscriptions (account_id, plan_code, status, usage_yyyymm, labels_used)
                VALUES (%s, %s, 'active', %s, 0)
                """,
                (account_id, plan_code, yyyymm),
            )
            cur.execute(
                "SELECT * FROM subscriptions WHERE account_id = %s",
                (account_id,),
            )
            return cur.fetchone()

        if row["usage_yyyymm"] != yyyymm:
            cur.execute(
                """
                UPDATE subscriptions
                SET usage_yyyymm = %s, labels_used = 0
                WHERE account_id = %s
                """,
                (yyyymm, account_id),
            )
            row["usage_yyyymm"] = yyyymm
            row["labels_used"] = 0
        return row


def quota_snapshot(sub: dict) -> dict[str, Any]:
    plan_code = sub["plan_code"]
    plan = get_plan(plan_code)
    used = int(sub["labels_used"])
    unlimited = bool(plan.get("labels_unlimited"))
    limit = plan.get("labels_per_month")
    return {
        "plan": plan_code,
        "used": used,
        "limit": None if unlimited else limit,
    }


def check_quota(sub: dict) -> tuple[bool, str, bool]:
    plan = get_plan(sub["plan_code"])
    if plan.get("labels_unlimited"):
        return True, "", False
    limit = plan.get("labels_per_month")
    if limit is None:
        return True, "", False
    used = int(sub["labels_used"])
    if used >= int(limit):
        mode = plan.get("overage_mode") or "block"
        if mode == "block":
            return False, "monthly_quota_exceeded", False
        return True, "", True
    return True, "", False


def increment_labels_used(account_id: int) -> dict:
    with db_cursor() as (_, cur):
        cur.execute(
            "SELECT * FROM subscriptions WHERE account_id = %s FOR UPDATE",
            (account_id,),
        )
        sub = cur.fetchone()
        cur.execute(
            "UPDATE subscriptions SET labels_used = labels_used + 1 WHERE account_id = %s",
            (account_id,),
        )
        sub["labels_used"] = int(sub["labels_used"]) + 1
    return sub
