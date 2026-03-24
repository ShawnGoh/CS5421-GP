import re
from conf.config import SOURCE_SCHEMA, TEST_SCHEMA


def sanitize_schema_prefixes(raw_sql: str) -> str:
    """
    Swaps any explicit SOURCE_SCHEMA references with the TEST_SCHEMA.
    """
    # Case-insensitive replacement of "source_schema." with "test_schema."
    return re.sub(
        rf"\b{SOURCE_SCHEMA}\.", f"{TEST_SCHEMA}.", raw_sql, flags=re.IGNORECASE
    )
