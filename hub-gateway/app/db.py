from contextlib import contextmanager
from typing import Iterator

import pymysql
from pymysql.connections import Connection

from app.config import settings


def get_connection() -> Connection:
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_username,
        password=settings.db_password,
        database=settings.db_database,
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


@contextmanager
def db_cursor() -> Iterator[tuple[Connection, pymysql.cursors.DictCursor]]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
