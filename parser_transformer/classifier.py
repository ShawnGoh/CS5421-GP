from util.log import log, LogTag
from compiler.contracts import StatementType, TableRef, ClassifiedStatement, RawCheckConstraint
import re

# Extracts Table Name/Schema and Classifies Statement type for later use

CREATE_TABLE_PREFIX = re.compile(r"^\s*CREATE\s+TABLE\s+", re.IGNORECASE)
ALTER_TABLE_PREFIX = re.compile(r"^\s*ALTER\s+TABLE\s+", re.IGNORECASE)

# =========================================================================================
# Skip white space
# =========================================================================================
def skip_whitespace(text: str, i: int) -> int:
    while i < len(text) and text[i].isspace():
        i += 1
    return i

def read_sql_identifier(text: str, start: int) -> tuple[str, int]:
    i = skip_whitespace(text, start)

    if i >= len(text):
        raise ValueError("Expected identifier, found end of input")

    if text[i] == '"':
        i += 1
        chars = []

        while i < len(text):
            if text[i] == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    chars.append('"')
                    i += 2
                    continue
                return "".join(chars), i + 1

            chars.append(text[i])
            i += 1

        raise ValueError("Unterminated quoted identifier")

    if not (text[i].isalpha() or text[i] == "_"):
        raise ValueError(f"Invalid identifier start: {text[i]!r}")

    start_i = i
    i += 1

    while i < len(text) and (text[i].isalnum() or text[i] in {"_", "$"}):
        i += 1

    return text[start_i:i], i

def read_qualified_name(text: str, start: int) -> tuple[TableRef, int]:
    first, i = read_sql_identifier(text, start)
    i = skip_whitespace(text, i)

    if i < len(text) and text[i] == ".":
        i += 1
        second, i = read_sql_identifier(text, i)
        return TableRef(schema_name=first, table_name=second), i

    return TableRef(schema_name=None, table_name=first), i


# =========================================================================================
# Extract top level parenthesized elements 
# - used to extract body CREATE TABLE TABLENAME (BODY)
# =========================================================================================

def extract_parenthesized(text: str, open_index: int) -> tuple[str, int]:
    if open_index >= len(text) or text[open_index] != "(":
        raise ValueError(f"Expected '(' at index {open_index}")

    i = open_index
    paren_depth = 0
    bracket_depth = 0
    in_single_quote = False
    in_double_quote = False

    while i < len(text):
        ch = text[i]

        if in_single_quote:
            if ch == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    i += 2
                    continue
                in_single_quote = False
            i += 1
            continue

        if in_double_quote:
            if ch == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    i += 2
                    continue
                in_double_quote = False
            i += 1
            continue

        if ch == "'":
            in_single_quote = True
            i += 1
            continue

        if ch == '"':
            in_double_quote = True
            i += 1
            continue

        if ch == "[":
            bracket_depth += 1
            i += 1
            continue

        if ch == "]":
            bracket_depth -= 1
            i += 1
            continue

        if ch == "(":
            paren_depth += 1
            i += 1
            continue

        if ch == ")":
            paren_depth -= 1
            if paren_depth == 0:
                inside = text[open_index + 1:i]
                return inside, i
            i += 1
            continue

        i += 1

    raise ValueError("Unbalanced parentheses")

# =========================================================================================
# Identify if the statement is create or alter otherwise unsupported type of statement
# =========================================================================================
def classify_statement(sql: str) -> StatementType:
    if sql.startswith("CREATE TABLE "):
        return StatementType.CREATE_TABLE

    if sql.startswith("ALTER TABLE "):
        return StatementType.ALTER_TABLE

    return StatementType.UNSUPPORTED

# =========================================================================================
# Extract table names from each statement type
# =========================================================================================
def extract_create_table_name(sql: str) -> TableRef:
    match = CREATE_TABLE_PREFIX.match(sql)
    if not match:
        raise ValueError("Not a CREATE TABLE statement")

    table_ref, _ = read_qualified_name(sql, match.end())
    return table_ref


def extract_alter_table_name(sql: str) -> TableRef:
    match = ALTER_TABLE_PREFIX.match(sql)
    if not match:
        raise ValueError("Not an ALTER TABLE statement")

    table_ref, _ = read_qualified_name(sql, match.end())
    return table_ref


def extract_table_ref(sql: str, stmt_type: StatementType) -> TableRef:
    if stmt_type == StatementType.CREATE_TABLE:
        return extract_create_table_name(sql)

    if stmt_type == StatementType.ALTER_TABLE:
        return extract_alter_table_name(sql)

    raise ValueError(f"Unsupported statement type: {stmt_type}")


# =========================================================================================
#  Wrapper to classify statement types + extract table names and references
# =========================================================================================

def classify_and_extract(sql: str) -> ClassifiedStatement:
    sql = sql.replace("\n", " ")
    sql = re.sub(r"\s+", " ", sql)
    sanitized = " ".join(sql.strip().upper().split())
    
    stmt_type = classify_statement(sanitized)

    if stmt_type == StatementType.UNSUPPORTED:
        raise ValueError("Unsupported statement")

    table_ref = extract_table_ref(sql, stmt_type)

    return ClassifiedStatement(
        statement_type=stmt_type,
        table_ref=table_ref,
        sanitized_sql=sanitized,
        original_sql=sql
    )
    