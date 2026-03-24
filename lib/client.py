import psycopg2
from psycopg2 import extensions
from typing import Generator
from contextlib import contextmanager

# Import the constants from your existing config.py
from conf.config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT


def get_connection() -> extensions.connection:
    """
    Returns a standard psycopg2 connection object using your config.py settings.
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


# if __name__ == "__main__":
#     # Test the connection
#     with db_session() as cursor:
#         cursor.execute("SELECT current_database();")
#         db_name = cursor.fetchone()[0]  # type: ignore
#         if db_name is None:
#             print("[-] Connection failed")
#             exit(1)
#         print(f"[+] Successfully connected to: {db_name}")
