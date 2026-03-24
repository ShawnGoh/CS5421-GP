from typing import List, Optional, Tuple
from psycopg2 import sql, extensions, Error
from conf.config import TEST_SCHEMA
from lib.sanitize import sanitize_schema_prefixes


def execute(cursor: extensions.cursor, raw_sql: str) -> Optional[List[Tuple]]:
    """
    Finalized Universal Runner:
    - Automatically redirects all SQL to the TEST_SCHEMA.
    - Sanitizes hardcoded schema prefixes.
    - Executes Procedures, Triggers, Functions, or Queries.
    """
    try:
        # 1. Logic Redirection (Prefixes)
        final_sql = sanitize_schema_prefixes(raw_sql)

        # 2. Context Redirection (Search Path)
        # This handles 'CREATE TABLE name' or 'CALL proc()' without prefixes
        cursor.execute(
            sql.SQL("SET search_path TO {}, public").format(sql.Identifier(TEST_SCHEMA))
        )

        # 3. Execute the raw SQL string
        cursor.execute(final_sql)

        # 4. Return results only if the command produces rows (SELECT/RETURNING)
        if cursor.description:
            return cursor.fetchall()

        return None

    except Error as e:
        # Provide clean feedback for debugging the generated SQL
        print(f"[-] Postgres Error in {TEST_SCHEMA}:")
        print(f"    Message: {e.pgerror}")
        raise e
