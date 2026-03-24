import psycopg2
from psycopg2 import extensions
from typing import Generator
from contextlib import contextmanager

from conf.config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT


def get_connection() -> extensions.connection:
    """
    Returns a standard psycopg2 connection object using config.py settings.
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
        )
        # Standard for DDL operations (CREATE/ALTER) in a compiler
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"[-] Failed to connect to {DB_NAME}: {e}")
        raise


@contextmanager
def db_session() -> Generator[extensions.cursor, None, None]:
    """
    Context manager that yields a cursor and ensures the connection
    closes after the block finishes.

    Usage:
        with db_session() as cur:
            cur.execute("SELECT...")
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
    finally:
        cur.close()
        conn.close()
