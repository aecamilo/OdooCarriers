from app.db import db_cursor


def iap_credit_balance(account_id: int) -> float:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT COALESCE(SUM(delta_credits), 0) AS balance
            FROM iap_credit_ledger WHERE account_id = %s
            """,
            (account_id,),
        )
        row = cur.fetchone()
    return float(row["balance"] or 0)


def add_iap_credits(account_id: int, delta: float, reason: str, reference_id: str | None = None) -> None:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO iap_credit_ledger (account_id, delta_credits, reason, reference_id)
            VALUES (%s, %s, %s, %s)
            """,
            (account_id, delta, reason, reference_id),
        )
