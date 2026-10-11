"""Bind and validate Odoo database.uuid per tenant account."""

from app.db import db_cursor


def validate_account_database_uuid(account_id: int, database_uuid: str) -> tuple[bool, str]:
    database_uuid = (database_uuid or "").strip().lower()
    if not database_uuid or len(database_uuid) < 8:
        return False, "invalid_database_uuid"

    with db_cursor() as (_, cur):
        cur.execute(
            "SELECT odoo_database_uuid FROM accounts WHERE id = %s FOR UPDATE",
            (account_id,),
        )
        row = cur.fetchone()
        if not row:
            return False, "invalid_token"

        stored = row.get("odoo_database_uuid")
        if stored:
            if str(stored).lower() != database_uuid:
                return False, "invalid_database_uuid"
            return True, ""

        cur.execute(
            """
            UPDATE accounts SET odoo_database_uuid = %s
            WHERE id = %s AND odoo_database_uuid IS NULL
            """,
            (database_uuid, account_id),
        )
    return True, ""
