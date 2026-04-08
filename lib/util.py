from pathlib import Path
from typing import Any, List, cast

import psycopg
from psycopg import Error, Rollback, pq, sql

from conf.config import SOURCE_SCHEMA, TEST_SCHEMA
from util.log import LogTag, log


def clone_schema(
    cursor: psycopg.Cursor, src: str = SOURCE_SCHEMA, dest: str = TEST_SCHEMA
):
    """
    Clones structure from source to destination.
    Creates destination schema if it doesn't exist.
    """
    # 1. Ensure the destination exists
    log(f"Ensuring schema '{dest}' exists...", LogTag.INFO)
    cursor.execute(
        sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(dest))
    )

    # 2. Get list of tables from the source schema
    cursor.execute(
        """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = %s 
        AND table_type = 'BASE TABLE'
    """,
        (src,),
    )

    tables = [row[0] for row in cursor.fetchall()]

    # 3. Clone each table structure
    for table in tables:
        log(f"    [+] Cloning table structure: {table}", LogTag.INFO)
        # INCLUDING ALL copies indexes, defaults, and native CHECK constraints
        cursor.execute(
            sql.SQL("CREATE TABLE {}.{} (LIKE {}.{} INCLUDING ALL)").format(
                sql.Identifier(dest),
                sql.Identifier(table),
                sql.Identifier(src),
                sql.Identifier(table),
            )
        )

    log(f"[+] Successfully cloned {len(tables)} tables to {dest}.", LogTag.INFO)


def drop_schema(
    cursor: psycopg.Cursor,
    schema_name: str = TEST_SCHEMA,
    if_exists: bool = True,
    cascade: bool = True,
) -> None:
    """
    Removes a schema and all its associated objects (tables, functions, triggers).
    """

    # Construct the query dynamically using the 'sql' module for safety
    query = sql.SQL("DROP SCHEMA ")

    if if_exists:
        query += sql.SQL("IF EXISTS ")

    query += sql.Identifier(schema_name)

    if cascade:
        query += sql.SQL(" CASCADE")

    try:
        log(f"Dropping schema: {schema_name} (Cascade={cascade})", LogTag.INFO)
        cursor.execute(query)
        log(f"Schema '{schema_name}' has been removed successfully.", LogTag.INFO)
    except Exception as e:
        log(f"Failed to drop schema '{schema_name}': {e}", LogTag.ERROR)
        raise e


def validate_sql_file(cursor: psycopg.Cursor[Any], file_path: Path) -> bool:
    """
    Dry-runs a multi-statement .sql file.
    Safely handles autocommit toggling only if not already in a transaction.
    """
    conn = cursor.connection

    # Check if we are already in a transaction block
    # IDLE means no transaction is active
    in_transaction = conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE

    original_autocommit = conn.autocommit

    try:
        # Only toggle autocommit if we aren't currently in a transaction
        if not in_transaction:
            conn.autocommit = False

        # conn.transaction() creates a SAVEPOINT if already INTRANS,
        # or a BEGIN if IDLE. This is the magic for nested transactions.
        with conn.transaction():
            content = file_path.read_text(encoding="utf-8")
            # cast(Any, ...) solves the Pylance LiteralString issue
            cursor.execute(sql.SQL(cast(Any, content)))

            # Force everything to undo
            raise Rollback

    except Rollback:
        return True
    except Error as e:
        log(f"Validation Failed: {e.diag.message_primary}", LogTag.ERROR)
        return False
    finally:
        # Only restore if we were the ones who changed it
        if not in_transaction:
            conn.autocommit = original_autocommit


def validate_sql_file_verbose(cursor: psycopg.Cursor[Any], file_path: Path) -> bool:
    conn = cursor.connection

    # Handle past transaction state
    status = conn.info.transaction_status
    is_idle = status == pq.TransactionStatus.IDLE
    if status == pq.TransactionStatus.INERROR:
        conn.rollback()
        is_idle = True

    original_autocommit = conn.autocommit
    changed_autocommit = False

    # Read and split by semicolon
    content = file_path.read_text(encoding="utf-8")
    statements = [s.strip() for s in content.split(";") if s.strip()]

    all_valid = True
    failed_statements: List[dict] = []

    log(f"Starting granular validation for: {file_path.name}", LogTag.INFO)

    try:
        # 2. Only toggle autocommit if we are IDLE
        if is_idle:
            conn.autocommit = False
            changed_autocommit = True

        # 3. Iterate through statements
        for i, stmt in enumerate(statements, 1):
            try:
                # conn.transaction() creates a checkpoint if already in a transaction,
                # continue the loop even if one statement fails.
                with conn.transaction():
                    cursor.execute(sql.SQL(cast(Any, stmt)))
            except Error as e:
                all_valid = False
                failed_statements.append(
                    {
                        "index": i,
                        "stmt": stmt[:50] + "..." if len(stmt) > 50 else stmt,
                        "error": e.diag.message_primary or str(e),
                    }
                )
    finally:
        # 4. Rollback everything done
        conn.rollback()

        # 5. Restore autocommit only if we were the ones who changed it
        if changed_autocommit:
            conn.autocommit = original_autocommit

    # Reporting
    if all_valid:
        log(f"All {len(statements)} statements passed.", LogTag.INFO)
    else:
        log(f"Found {len(failed_statements)} errors in {file_path.name}:", LogTag.ERROR)
        for failure in failed_statements:
            log(f"Statement #{failure['index']}: {failure['error']}", LogTag.ERROR)
            log(f"SQL Snippet: {failure['stmt']}\n", LogTag.ERROR)

    return all_valid
