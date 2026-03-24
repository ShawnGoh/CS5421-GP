from psycopg2 import sql, extensions

from conf.config import SOURCE_SCHEMA, TEST_SCHEMA


def clone_schema(
    cursor: extensions.cursor, src: str = SOURCE_SCHEMA, dest: str = TEST_SCHEMA
):
    """
    Clones structure from source to destination.
    Creates destination schema if it doesn't exist.
    """
    # 1. Ensure the destination exists
    print(f"[*] Ensuring schema '{dest}' exists...")
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
        print(f"    [+] Cloning table structure: {table}")
        # INCLUDING ALL copies indexes, defaults, and native CHECK constraints
        cursor.execute(
            sql.SQL("CREATE TABLE {}.{} (LIKE {}.{} INCLUDING ALL)").format(
                sql.Identifier(dest),
                sql.Identifier(table),
                sql.Identifier(src),
                sql.Identifier(table),
            )
        )

    print(f"[+] Successfully cloned {len(tables)} tables to {dest}.")


def drop_schema(
    cursor: extensions.cursor,
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
        print(f"[*] Dropping schema: {schema_name} (Cascade={cascade})")
        cursor.execute(query)
        print(f"[+] Schema '{schema_name}' has been removed successfully.")
    except Exception as e:
        print(f"[-] Failed to drop schema '{schema_name}': {e}")
        raise e
