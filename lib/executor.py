from typing import List, Optional, Tuple, Any
from psycopg import sql, Cursor, Error

from conf.config import TEST_SCHEMA
from lib.sanitize import sanitize_schema_prefixes


def execute(cursor: Cursor, raw_sql: str) -> Optional[List[Tuple[Any, ...]]]:
    try:
        # 1. Logic Redirection (Prefixes)
        final_sql = sanitize_schema_prefixes(raw_sql)

        # 2. Context Redirection (Search Path)
        cursor.execute(
            sql.SQL("SET search_path TO {}, public").format(sql.Identifier(TEST_SCHEMA))
        )

        # 3. Execute the SQL object
        cursor.execute(final_sql)

        if cursor.description:
            return cursor.fetchall()
        return None

    except Error as e:
        print(f"[-] Postgres Error: {e}")
        raise e


def validate_sql(cursor: Cursor, raw_sql: str) -> bool:
    try:
        with cursor.connection.transaction(force_rollback=True):
            cursor.execute(
                sql.SQL("SET search_path TO {}, public").format(
                    sql.Identifier(TEST_SCHEMA)
                )
            )

            final_sql = sanitize_schema_prefixes(raw_sql)

            cursor.execute(final_sql)
            return True
    except Error as e:
        print(f"[-] Validation Failed: {e}")
        raise e
