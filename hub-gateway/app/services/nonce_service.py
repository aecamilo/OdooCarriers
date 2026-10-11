from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db import db_cursor


def register_nonce(nonce: str, account_id: int) -> bool:
    ttl = max(settings.sc_hmac_max_skew_sec * 2, 600)
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl)
    with db_cursor() as (_, cur):
        cur.execute("DELETE FROM hmac_nonces WHERE expires_at < UTC_TIMESTAMP(3)")
        try:
            cur.execute(
                """
                INSERT INTO hmac_nonces (nonce, account_id, expires_at)
                VALUES (%s, %s, %s)
                """,
                (nonce, account_id, expires.replace(tzinfo=None)),
            )
            return True
        except Exception:
            return False
