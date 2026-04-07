import psycopg
from typing import Generator
from contextlib import contextmanager

from conf.config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT


def get_connection() -> psycopg.Connection:
    conn_str = (
        f"host={DB_HOST} "
        f"dbname={DB_NAME} "
        f"user={DB_USER} "
        f"password={DB_PASSWORD} "
        f"port={DB_PORT}"
    )

    try:
        conn = psycopg.connect(conn_str, autocommit=False) # set as false for validator deferred checks
        print(f"[+] Connected to psycopg3: {DB_NAME}")
        return conn
    except Exception as e:
        print(f"[-] Connection failed: {e}")
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
        print("[*] Database session closed.")
