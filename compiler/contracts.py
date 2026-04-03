from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

# =========================
# Enums
# =========================

class LiteralType(str, Enum):
    STRING = "STRING"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    NULL = "NULL"


class TruthValue(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"

# =========================
# Base expression classes
# =========================

class Expr:
    pass


class BoolExpr(Expr):
    pass


# =========================
# Scalar expressions
# =========================

@dataclass(frozen=True)
class ColumnExpr(Expr):
    original_name: str
    trigger_reference: str   # e.g. NEW.price


@dataclass(frozen=True)
class LiteralExpr(Expr):
    value: Any
    literal_type: LiteralType


@dataclass(frozen=True)
class FunctionExpr(Expr):
    function_name: str
    args: list[Expr]


# =========================
# Boolean expressions
# =========================

@dataclass(frozen=True)
class CompareExpr(BoolExpr):
    left: Expr
    operator: str
    right: Expr


@dataclass(frozen=True)
class AndExpr(BoolExpr):
    left: BoolExpr
    right: BoolExpr


@dataclass(frozen=True)
class OrExpr(BoolExpr):
    left: BoolExpr
    right: BoolExpr


@dataclass(frozen=True)
class NotExpr(BoolExpr):
    expr: BoolExpr


@dataclass(frozen=True)
class IsNullExpr(BoolExpr):
    expr: Expr
    negated: bool = False


@dataclass(frozen=True)
class BetweenExpr(BoolExpr):
    value: Expr
    lower: Expr
    upper: Expr
    negated: bool = False


@dataclass(frozen=True)
class InExpr(BoolExpr):
    value: Expr
    options: list[Expr]
    negated: bool = False

@dataclass(frozen=True)
class FunctionExpr(Expr):
    function_name: str
    args: list[Expr]

@dataclass(frozen=True)
class UnaryValueExpr(Expr):
    operator: str
    expr: Expr

@dataclass(frozen=True)
class BinaryValueExpr(Expr):
    left: Expr
    operator: str
    right: Expr

@dataclass(frozen=True)
class LikeExpr(Expr):
    value: Expr
    pattern: Expr
    negated: bool = False
    case_insensitive: bool = False   # for ILIKE

@dataclass(frozen=True)
class BoolLiteralExpr(BoolExpr):
    value: bool | None

@dataclass(frozen=True)
class IsBoolExpr(BoolExpr):
    expr: BoolExpr
    check_for: str   # "TRUE", "FALSE", "UNKNOWN"
    negated: bool = False

@dataclass(frozen=True)
class CastExpr(Expr):
    expr: Expr
    target_type: str   # "NUMERIC", "TEXT", etc.
    use_pg_style: bool = True   # True: ::, False: CAST()

# =========================
# Top-level transformed IR
# =========================

@dataclass(frozen=True)
class TransformedCheckConstraint:
    table_name: str
    constraint_name: str
    condition: BoolExpr
    referenced_columns: list[tuple[str, str]] # e.g. [("price", "NUMERIC"), ("status", "TEXT")]
    original_check_sql: str

# =========================
# Codegen output
# =========================

@dataclass(frozen=True)
class OutputCheck:
    procedure_name: str
    function_name: str
    trigger_name: str
    procedure_sql: str
    function_sql: str
    trigger_sql: str
    combined_sql: str

# =========================
# Sematic Evaluator
# =========================

class TruthValue(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"

# =========================
# Validator
# =========================

@dataclass(frozen=True)
class TestRow:
    values: dict[str, Any]


@dataclass(frozen=True)
class TestRowExpectation:
    row: TestRow
    expected_truth: TruthValue
    rationale: str


@dataclass(frozen=True)
class TestCaseResult:
    row: TestRow
    expected_truth: TruthValue
    actual_truth: TruthValue | None
    expected_pass: bool
    actual_pass: bool
    rationale: str
    execution_message: str = ""


@dataclass(frozen=True)
class ValidationRequest:
    constraint: TransformedCheckConstraint
    artifacts: GeneratedCheckArtifacts


@dataclass(frozen=True)
class ValidationResult:
    success: bool
    test_case_results: list[TestCaseResult]
    errors: list[str]
    summary: str