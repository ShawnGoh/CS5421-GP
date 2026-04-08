from contextlib import contextmanager
from typing import Generator

import psycopg

from conf.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from util.log import LogTag, log


def get_connection() -> psycopg.Connection:
    conn_str = (
        f"host={DB_HOST} "
        f"dbname={DB_NAME} "
        f"user={DB_USER} "
        f"password={DB_PASSWORD} "
        f"port={DB_PORT}"
    )

    try:
        conn = psycopg.connect(
            conn_str, autocommit=False
        )  # set as false for validator deferred checks
        log(f"[+] Connected to psycopg3: {DB_NAME}", LogTag.INFO)
        return conn
    except Exception as e:
        log(f"[-] Connection failed: {e}", LogTag.ERROR)
        raise


@contextmanager
def db_session() -> Generator[psycopg.Cursor, None, None]:
    conn = get_connection()
    cur = conn.cursor()

    try:
        yield cur
    finally:
        cur.close()
        conn.close()
        log("Database session closed.", LogTag.INFO)
