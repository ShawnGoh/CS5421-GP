import re

from psycopg import sql

from conf.config import SOURCE_SCHEMA, TEST_SCHEMA


def sanitize_schema_prefixes(raw_sql: str) -> sql.SQL:
    """
    Swaps any explicit SOURCE_SCHEMA references with the TEST_SCHEMA.
    """
    # Case-insensitive replacement of "source_schema." with "test_schema."

    sanitized_string = re.sub(
        rf"\b{SOURCE_SCHEMA}\.", f"{TEST_SCHEMA}.", raw_sql, flags=re.IGNORECASE
    )

    return sql.SQL(sanitized_string)  # type: ignore
