from datetime import datetime, timezone

from app.db import db_cursor
from app.services.plan_catalog import get_plan


def check_rate_limit(account_id: int, plan_code: str) -> tuple[bool, str]:
    plan = get_plan(plan_code)
    rpm = int(plan.get("rpm") or 10)
    burst = int(plan.get("burst") or 2)
    now = datetime.now(timezone.utc)
    window_key = now.strftime("%Y%m%d%H%M")

    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT request_count, burst_count, last_request_at
            FROM rate_limit_windows
            WHERE account_id = %s AND window_key = %s
            FOR UPDATE
            """,
            (account_id, window_key),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                """
                INSERT INTO rate_limit_windows
                (account_id, window_key, request_count, burst_count, last_request_at)
                VALUES (%s, %s, 1, 1, UTC_TIMESTAMP(3))
                """,
                (account_id, window_key),
            )
            return True, ""

        req = int(row["request_count"]) + 1
        if req > rpm:
            return False, "rate_limit_exceeded"

        burst_count = int(row["burst_count"] or 0)
        last_at = row["last_request_at"]
        if last_at:
            delta = (now.replace(tzinfo=None) - last_at).total_seconds()
            if delta < 1.0:
                burst_count += 1
            else:
                burst_count = 1
        else:
            burst_count = 1

        if burst_count > burst:
            return False, "rate_limit_exceeded"

        cur.execute(
            """
            UPDATE rate_limit_windows
            SET request_count = %s, burst_count = %s, last_request_at = UTC_TIMESTAMP(3)
            WHERE account_id = %s AND window_key = %s
            """,
            (req, burst_count, account_id, window_key),
        )
    return True, ""
