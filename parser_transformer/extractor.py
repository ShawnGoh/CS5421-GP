from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import re

from compiler.contracts import StatementType, ClassifiedStatement

@dataclass(frozen=True)
class RawCheckConstraint:
    table_name: str
    constraint_name: str
    check_expr_sql: str
    original_check_sql: str
    source_element_sql: str
    column_name: Optional[str] = None


# =========================
# Regex helpers
# =========================

CREATE_TABLE_PREFIX = re.compile(r"^\s*CREATE\s+TABLE\s+", re.IGNORECASE)
ALTER_TABLE_PREFIX = re.compile(r"^\s*ALTER\s+TABLE\s+", re.IGNORECASE)
ADD_CONSTRAINT_PREFIX = re.compile(r"\s*ADD\s+CONSTRAINT\s+", re.IGNORECASE)
CHECK_PREFIX = re.compile(r"\s*CHECK\s*\(", re.IGNORECASE)
NAMED_CHECK_PREFIX = re.compile(r"^\s*CONSTRAINT\s+([A-Za-z_][A-Za-z0-9_$]*)\s+CHECK\s*\(", re.IGNORECASE)
CHECK_KEYWORD = re.compile(r"\bCHECK\s*\(", re.IGNORECASE)


# =========================
# Helper Functions
# =========================

def skip_whitespace(text: str, i: int) -> int:
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def read_sql_identifier(text: str, start: int) -> tuple[str, int]:
    i = skip_whitespace(text, start)

    if i >= len(text):
        raise ValueError("Expected identifier, found end of input")

    # Quoted identifier
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

    # Bare identifier
    if not (text[i].isalpha() or text[i] == "_"):
        raise ValueError(f"Invalid identifier start at index {i}: {text[i]!r}")

    start_i = i
    i += 1

    while i < len(text) and (text[i].isalnum() or text[i] in {"_", "$"}):
        i += 1

    return text[start_i:i], i


def read_qualified_name(text: str, start: int) -> tuple[tuple[Optional[str], str], int]:
    first, i = read_sql_identifier(text, start)
    i = skip_whitespace(text, i)

    if i < len(text) and text[i] == ".":
        i += 1
        second, i = read_sql_identifier(text, i)
        return (first, second), i

    return (None, first), i


# =========================
# Core scanners
# =========================

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


def split_top_level_commas(text: str) -> list[str]:
    parts = []
    current = []

    paren_depth = 0
    bracket_depth = 0
    in_single_quote = False
    in_double_quote = False

    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if in_single_quote:
            current.append(ch)
            if ch == "'":
                if i + 1 < n and text[i + 1] == "'":
                    current.append(text[i + 1])
                    i += 2
                    continue
                in_single_quote = False
            i += 1
            continue

        if in_double_quote:
            current.append(ch)
            if ch == '"':
                if i + 1 < n and text[i + 1] == '"':
                    current.append(text[i + 1])
                    i += 2
                    continue
                in_double_quote = False
            i += 1
            continue

        if ch == "'":
            in_single_quote = True
            current.append(ch)
            i += 1
            continue

        if ch == '"':
            in_double_quote = True
            current.append(ch)
            i += 1
            continue

        if ch == "(":
            paren_depth += 1
            current.append(ch)
            i += 1
            continue

        if ch == ")":
            paren_depth -= 1
            current.append(ch)
            i += 1
            continue

        if ch == "[":
            bracket_depth += 1
            current.append(ch)
            i += 1
            continue

        if ch == "]":
            bracket_depth -= 1
            current.append(ch)
            i += 1
            continue

        if ch == "," and paren_depth == 0 and bracket_depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            i += 1
            continue

        current.append(ch)
        i += 1

    part = "".join(current).strip()
    if part:
        parts.append(part)

    return parts


# =========================
# CREATE TABLE body extraction
# =========================

def extract_create_table_body(sql: str) -> str:
    match = CREATE_TABLE_PREFIX.match(sql)
    if not match:
        raise ValueError("Not a CREATE TABLE statement")

    _, idx = read_qualified_name(sql, match.end())
    idx = skip_whitespace(sql, idx)

    if idx >= len(sql) or sql[idx] != "(":
        raise ValueError("Expected '(' after CREATE TABLE name")

    body, _ = extract_parenthesized(sql, idx)
    return body


# =========================
# CREATE TABLE check extraction
# =========================

def extract_named_table_check(table_name: str, element: str) -> RawCheckConstraint:
    m = NAMED_CHECK_PREFIX.match(element)
    if not m:
        raise ValueError("Invalid named table-level CHECK element")

    constraint_name = m.group(1)
    check_idx = element.upper().find("CHECK")
    open_idx = element.find("(", check_idx)
    check_expr_sql, close_idx = extract_parenthesized(element, open_idx)

    return RawCheckConstraint(
        table_name=table_name,
        constraint_name=constraint_name,
        check_expr_sql=check_expr_sql.strip(),
        original_check_sql=element[check_idx:close_idx + 1].strip(),
        source_element_sql=element,
        column_name=None,
    )


def extract_unnamed_table_check(table_name: str, element: str, counter: int) -> RawCheckConstraint:
    constraint_name = f"{table_name}_check_{counter}"
    check_idx = element.upper().find("CHECK")
    open_idx = element.find("(", check_idx)
    check_expr_sql, close_idx = extract_parenthesized(element, open_idx)

    return RawCheckConstraint(
        table_name=table_name,
        constraint_name=constraint_name,
        check_expr_sql=check_expr_sql.strip(),
        original_check_sql=element[check_idx:close_idx + 1].strip(),
        source_element_sql=element,
        column_name=None,
    )


def extract_column_level_check(table_name: str, element: str) -> RawCheckConstraint:
    column_name, _ = read_sql_identifier(element, 0)

    check_match = CHECK_KEYWORD.search(element)
    if not check_match:
        raise ValueError("Column definition does not contain CHECK")

    open_idx = element.find("(", check_match.start())
    check_expr_sql, close_idx = extract_parenthesized(element, open_idx)

    constraint_name = f"{table_name}_{column_name}_check"

    return RawCheckConstraint(
        table_name=table_name,
        constraint_name=constraint_name,
        check_expr_sql=check_expr_sql.strip(),
        original_check_sql=element[check_match.start():close_idx + 1].strip(),
        source_element_sql=element,
        column_name=column_name,
    )


def extract_checks_from_create_body(table_name: str, body_sql: str) -> list[RawCheckConstraint]:
    elements = split_top_level_commas(body_sql)
    out: list[RawCheckConstraint] = []
    unnamed_counter = 1

    for element in elements:
        element = element.strip()
        normalized = " ".join(element.upper().split())

        # Named table-level: CONSTRAINT x CHECK (...)
        if NAMED_CHECK_PREFIX.match(element):
            out.append(extract_named_table_check(table_name, element))
            continue

        # Unnamed table-level: CHECK (...)
        if normalized.startswith("CHECK(") or normalized.startswith("CHECK "):
            out.append(extract_unnamed_table_check(table_name, element, unnamed_counter))
            unnamed_counter += 1
            continue

        # Column-level: col type ... CHECK (...)
        if CHECK_KEYWORD.search(element):
            out.append(extract_column_level_check(table_name, element))
            continue

    return out


# =========================
# ALTER TABLE check extraction
# =========================

def extract_check_from_alter_table(sql: str) -> RawCheckConstraint:
    alter_match = ALTER_TABLE_PREFIX.match(sql)
    if not alter_match:
        raise ValueError("Not an ALTER TABLE statement")

    (schema_name, table_name), idx = read_qualified_name(sql, alter_match.end())

    add_match = ADD_CONSTRAINT_PREFIX.match(sql, idx)
    if not add_match:
        raise ValueError("Only ALTER TABLE ... ADD CONSTRAINT ... is supported")

    constraint_name, idx = read_sql_identifier(sql, add_match.end())

    check_match = CHECK_PREFIX.match(sql, idx)
    if not check_match:
        raise ValueError("Expected CHECK (...) after constraint name")

    open_idx = check_match.end() - 1
    check_expr_sql, close_idx = extract_parenthesized(sql, open_idx)
    original_check_sql = sql[check_match.start():close_idx + 1].strip()

    return RawCheckConstraint(
        table_name=table_name,
        constraint_name=constraint_name,
        check_expr_sql=check_expr_sql.strip(),
        original_check_sql=original_check_sql,
        source_element_sql=sql,
        column_name=None,
    )


# =========================
# Unified Wrapper
# =========================

def extract_raw_checks_from_statement(classified_stmt: ClassifiedStatement) -> list[RawCheckConstraint]:
    if classified_stmt.statement_type == StatementType.CREATE_TABLE:
        return extract_checks_from_create_body(
            table_name=classified_stmt.table_ref.table_name,
            body_sql=extract_create_table_body(classified_stmt.original_sql),
        )

    if classified_stmt.statement_type == StatementType.ALTER_TABLE:
        return [extract_check_from_alter_table(classified_stmt.original_sql)]

    return []


# =========================
# Extract schema from sql body
# =========================

def extract_table_schema_from_original_sql(sql: str) -> dict[str, str]:
    body_sql = extract_create_table_body(sql=sql)
    elements = split_top_level_commas(body_sql)
    schema = {}

    for element in elements:
        element = element.strip()

        upper = element.upper()
        if upper.startswith("CONSTRAINT") or upper.startswith("CHECK"):
            continue

        col_name, idx = read_sql_identifier(element, 0)
        rest = element[idx:].strip()

        # crude v1: type is first token after column name
        type_name = rest.split()[0].upper()
        schema[col_name] = type_name

    return schema