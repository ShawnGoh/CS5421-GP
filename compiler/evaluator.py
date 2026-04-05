import re

from compiler.contracts import (
    AndExpr,
    BetweenExpr,
    BinaryValueExpr,
    BoolLiteralExpr,
    CastExpr,
    ColumnExpr,
    CompareExpr,
    Expr,
    FunctionExpr,
    InExpr,
    IsBoolExpr,
    IsNullExpr,
    LikeExpr,
    LiteralExpr,
    NotExpr,
    OrExpr,
    TestRow,
    TruthValue,
    UnaryValueExpr,
)

class ConstraintSemanticEvaluator:
    def evaluate(self, expr, row: TestRow) -> TruthValue:
        if isinstance(expr, BoolLiteralExpr):
            if expr.value is True:
                return TruthValue.TRUE
            if expr.value is False:
                return TruthValue.FALSE
            return TruthValue.UNKNOWN

        if isinstance(expr, AndExpr):
            left = self.evaluate(expr.left, row)
            right = self.evaluate(expr.right, row)
            return self._and_truth(left, right)

        if isinstance(expr, OrExpr):
            left = self.evaluate(expr.left, row)
            right = self.evaluate(expr.right, row)
            return self._or_truth(left, right)

        if isinstance(expr, NotExpr):
            inner = self.evaluate(expr.inner, row)
            return self._not_truth(inner)

        if isinstance(expr, CompareExpr):
            left = self._eval_scalar(expr.left, row)
            right = self._eval_scalar(expr.right, row)
            return self._compare(left, expr.operator, right)

        if isinstance(expr, IsNullExpr):
            value = self._eval_scalar(expr.expr, row)
            is_null = value is None
            if expr.negated:
                return TruthValue.FALSE if is_null else TruthValue.TRUE
            return TruthValue.TRUE if is_null else TruthValue.FALSE

        if isinstance(expr, BetweenExpr):
            value = self._eval_scalar(expr.value, row)
            lower = self._eval_scalar(expr.lower, row)
            upper = self._eval_scalar(expr.upper, row)

            if value is None or lower is None or upper is None:
                result = TruthValue.UNKNOWN
            else:
                result = TruthValue.TRUE if lower <= value <= upper else TruthValue.FALSE

            return self._not_truth(result) if expr.negated else result

        if isinstance(expr, InExpr):
            value = self._eval_scalar(expr.value, row)
            options = [self._eval_scalar(opt, row) for opt in expr.options]

            if value is None:
                result = TruthValue.UNKNOWN
            else:
                result = TruthValue.TRUE if value in options else TruthValue.FALSE

            return self._not_truth(result) if expr.negated else result
        
        if isinstance(expr, LikeExpr):
            value = self._eval_scalar(expr.value, row)
            pattern = self._eval_scalar(expr.pattern, row)

            if value is None or pattern is None:
                return TruthValue.UNKNOWN

            regex = self._like_to_regex(str(pattern))
            flags = re.IGNORECASE if expr.case_insensitive else 0
            matched = re.fullmatch(regex, str(value), flags=flags) is not None

            result = TruthValue.TRUE if matched else TruthValue.FALSE
            return self._not_truth(result) if expr.negated else result

        if isinstance(expr, IsBoolExpr):
            val = self._eval_truth_target(expr.expr, row)

            if expr.check_for == "TRUE":
                result = TruthValue.TRUE if val == TruthValue.TRUE else TruthValue.FALSE
            elif expr.check_for == "FALSE":
                result = TruthValue.TRUE if val == TruthValue.FALSE else TruthValue.FALSE
            elif expr.check_for == "UNKNOWN":
                result = TruthValue.TRUE if val == TruthValue.UNKNOWN else TruthValue.FALSE
            else:
                raise ValueError(f"Unsupported truth check: {expr.check_for}")

            return self._not_truth(result) if expr.negated else result

        raise TypeError(f"Unsupported BoolExpr: {type(expr).__name__}")

    def _eval_truth_target(self, expr, row: TestRow) -> TruthValue:
        if isinstance(expr, (AndExpr, OrExpr, NotExpr, CompareExpr, IsNullExpr,
                             BetweenExpr, InExpr, LikeExpr, BoolLiteralExpr, IsBoolExpr)):
            return self.evaluate(expr, row)

        value = self._eval_scalar(expr, row)
        if value is None:
            return TruthValue.UNKNOWN
        if value is True:
            return TruthValue.TRUE
        if value is False:
            return TruthValue.FALSE

        raise ValueError("IS TRUE / IS FALSE / IS UNKNOWN expects a boolean-valued expression")


    def _eval_scalar(self, expr, row: TestRow):
        if isinstance(expr, ColumnExpr):
            return row.values.get(expr.original_name) # read value from row

        if isinstance(expr, LiteralExpr):
            return expr.value

        if isinstance(expr, BinaryValueExpr):
            left = self._eval_scalar(expr.left, row)
            right = self._eval_scalar(expr.right, row)

            if left is None or right is None:
                return None

            if expr.operator == "+":
                return left + right
            if expr.operator == "-":
                return left - right
            if expr.operator == "*":
                return left * right
            if expr.operator == "/":
                return left / right
            if expr.operator == "%":
                return left % right

            raise ValueError(f"Unsupported arithmetic operator: {expr.operator}")

        if isinstance(expr, UnaryValueExpr):
            value = self._eval_scalar(expr.expr, row)
            if value is None:
                return None
            if expr.operator == "+":
                return +value
            if expr.operator == "-":
                return -value
            raise ValueError(f"Unsupported unary operator: {expr.operator}")

        if isinstance(expr, FunctionExpr):
            return self._eval_function(expr, row)

        if isinstance(expr, CastExpr):
            value = self._eval_scalar(expr.expr, row)
            if value is None:
                return None

            target = expr.target_type.upper()
            if target in {"NUMERIC", "DECIMAL", "FLOAT", "DOUBLE PRECISION", "REAL"}:
                return float(value)
            if target in {"INT", "INTEGER", "BIGINT", "SMALLINT"}:
                return int(value)
            if target in {"TEXT", "VARCHAR", "CHAR", "CHARACTER VARYING"}:
                return str(value)
            if target == "BOOLEAN":
                if isinstance(value, bool):
                    return value
                if str(value).lower() in {"true", "t", "1"}:
                    return True
                if str(value).lower() in {"false", "f", "0"}:
                    return False
                raise ValueError(f"Cannot cast to BOOLEAN: {value}")

            return value

        raise TypeError(f"Unsupported Expr: {type(expr).__name__}")

    def _eval_function(self, expr: FunctionExpr, row: TestRow):
        fn = expr.function_name.lower()
        args = [self._eval_scalar(arg, row) for arg in expr.args]

        if fn == "char_length":
            return None if args[0] is None else len(str(args[0]))
        if fn == "length":
            return None if args[0] is None else len(str(args[0]))
        if fn == "abs":
            return None if args[0] is None else abs(args[0])
        if fn == "lower":
            return None if args[0] is None else str(args[0]).lower()
        if fn == "upper":
            return None if args[0] is None else str(args[0]).upper()

        raise ValueError(f"Unsupported function: {expr.function_name}")

    def _compare(self, left, operator: str, right) -> TruthValue:
        if left is None or right is None:
            return TruthValue.UNKNOWN

        if operator == "=":
            return TruthValue.TRUE if left == right else TruthValue.FALSE
        if operator in {"!=", "<>"}:
            return TruthValue.TRUE if left != right else TruthValue.FALSE
        if operator == "<":
            return TruthValue.TRUE if left < right else TruthValue.FALSE
        if operator == "<=":
            return TruthValue.TRUE if left <= right else TruthValue.FALSE
        if operator == ">":
            return TruthValue.TRUE if left > right else TruthValue.FALSE
        if operator == ">=":
            return TruthValue.TRUE if left >= right else TruthValue.FALSE

        raise ValueError(f"Unsupported comparison operator: {operator}")

    def _not_truth(self, value: TruthValue) -> TruthValue:
        if value == TruthValue.TRUE:
            return TruthValue.FALSE
        if value == TruthValue.FALSE:
            return TruthValue.TRUE
        return TruthValue.UNKNOWN

    def _and_truth(self, left: TruthValue, right: TruthValue) -> TruthValue:
        if left == TruthValue.FALSE or right == TruthValue.FALSE:
            return TruthValue.FALSE 
        if left == TruthValue.TRUE and right == TruthValue.TRUE:
            return TruthValue.TRUE
        return TruthValue.UNKNOWN

    def _or_truth(self, left: TruthValue, right: TruthValue) -> TruthValue:
        if left == TruthValue.TRUE or right == TruthValue.TRUE:
            return TruthValue.TRUE 
        if left == TruthValue.FALSE and right == TruthValue.FALSE:
            return TruthValue.FALSE
        return TruthValue.UNKNOWN

    def _like_to_regex(self, pattern: str) -> str:
        escaped = re.escape(pattern)
        escaped = escaped.replace(r"\%", ".*")
        escaped = escaped.replace(r"\_", ".")
        return escaped  





        
