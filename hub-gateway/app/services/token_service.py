import hashlib
import secrets
from typing import Optional

from app.config import settings
from app.db import db_cursor


def hash_token(token: str) -> bytes:
    pepper = settings.saas_key_pepper or ""
    digest = hashlib.sha256((token + pepper).encode("utf-8")).digest()
    return digest


def hash_iap_account_token(account_token: str) -> bytes:
    pepper = settings.saas_key_pepper or ""
    return hashlib.sha256((account_token + pepper).encode("utf-8")).digest()


def generate_api_token() -> str:
    return secrets.token_urlsafe(32)


def resolve_account_by_token(token: str) -> Optional[int]:
    if not token or len(token) < 16:
        return None
    th = hash_token(token)
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT a.id, a.status
            FROM api_token_hashes t
            JOIN accounts a ON a.id = t.account_id
            WHERE t.token_hash = %s
            LIMIT 1
            """,
            (th,),
        )
        row = cur.fetchone()
    if not row or row["status"] != "active":
        return None
    return int(row["id"])


def store_api_token(account_id: int, token: str) -> None:
    th = hash_token(token)
    with db_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO api_token_hashes (account_id, token_hash, rotated_at)
            VALUES (%s, %s, UTC_TIMESTAMP(3))
            ON DUPLICATE KEY UPDATE token_hash = VALUES(token_hash), rotated_at = UTC_TIMESTAMP(3)
            """,
            (account_id, th),
        )
