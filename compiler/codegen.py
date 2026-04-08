from compiler.contracts import (
    AndExpr,
    BetweenExpr,
    BinaryValueExpr,
    BoolExpr,
    BoolLiteralExpr,
    CastExpr,
    ColumnExpr,
    CompareExpr,
    ExistsExpr,
    Expr,
    LikeExpr,
    FunctionExpr,
    InExpr,
    IsBoolExpr,
    IsNullExpr,
    LiteralExpr,
    LiteralType,
    NotExpr,
    OrExpr,
    UnaryValueExpr,
    TransformedCheckConstraint,
    OutputCheck,
)

class CheckCodeGenerator:
    def generate(self, constraint: TransformedCheckConstraint) -> OutputCheck:
        function_name = f"trigger_function_{constraint.table_name}_{constraint.constraint_name}"
        trigger_name = f"trigger_{constraint.table_name}_{constraint.constraint_name}"

        if isinstance(constraint.condition, ExistsExpr):
            function_sql = self._build_global_query_trigger_function_sql(
                constraint,
                function_name,
            )
            trigger_sql = self._build_constraint_trigger_sql(
                trigger_name,
                constraint.table_name,
                function_name,
            )
        else:
            function_sql = self._build_row_trigger_function_sql(
                constraint,
                function_name,
            )
            trigger_sql = self._build_trigger_sql(
                trigger_name,
                constraint.table_name,
                function_name,
            )

        combined_sql = function_sql + "\n\n" + trigger_sql

        return OutputCheck(
            procedure_name=None,
            function_name=function_name,
            trigger_name=trigger_name,
            procedure_sql=None,
            function_sql=function_sql,
            trigger_sql=trigger_sql,
            combined_sql=combined_sql,
        )

    def _build_row_trigger_function_sql(
        self,
        constraint: TransformedCheckConstraint,
        function_name: str,
    ) -> str:
        condition_sql = self._emit_bool_expr_for_trigger(constraint.condition)
        escaped_message = constraint.original_check_sql.replace("'", "''").replace("%", "%%")

        return f"""
CREATE OR REPLACE FUNCTION {function_name}()
RETURNS TRIGGER AS $$
BEGIN
    IF ({condition_sql}) IS FALSE THEN
        RAISE EXCEPTION USING MESSAGE = 'CHECK constraint violated: {escaped_message}';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""".strip()

    def _build_global_query_trigger_function_sql(
        self,
        constraint: TransformedCheckConstraint,
        function_name: str,
    ) -> str:
        if not isinstance(constraint.condition, ExistsExpr):
            raise TypeError(
                f"Global raw-query trigger function expects ExistsExpr, got {type(constraint.condition).__name__}"
            )

        violation_condition = self._emit_violation_condition_for_global_query(constraint.condition)
        escaped_message = constraint.original_check_sql.replace("'", "''").replace("%", "%%")

        return f"""
CREATE OR REPLACE FUNCTION {function_name}()
RETURNS TRIGGER AS $$
BEGIN
    IF {violation_condition} THEN
        RAISE EXCEPTION USING MESSAGE = 'CHECK constraint violated: {escaped_message}';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
""".strip()

    def _build_global_query_trigger_function_sql(
        self,
        constraint: TransformedCheckConstraint,
        function_name: str,
    ) -> str:
        if not isinstance(constraint.condition, ExistsExpr):
            raise TypeError(
                f"Global raw-query trigger function expects ExistsExpr, got {type(constraint.condition).__name__}"
            )

        violation_condition = self._emit_violation_condition_for_global_query(constraint.condition)
        escaped_message = constraint.original_check_sql.replace("'", "''").replace("%", "%%")

        return f"""
CREATE OR REPLACE FUNCTION {function_name}()
RETURNS TRIGGER AS $$
BEGIN
    IF {violation_condition} THEN
        RAISE EXCEPTION USING MESSAGE = 'CHECK constraint violated: {escaped_message}';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
""".strip()

    def _build_trigger_sql(
        self,
        trigger_name: str,
        table_name: str,
        function_name: str,
    ) -> str:
        return f"""
DROP TRIGGER IF EXISTS {trigger_name} ON {table_name};
CREATE TRIGGER {trigger_name}
BEFORE INSERT OR UPDATE ON {table_name}
FOR EACH ROW
EXECUTE FUNCTION {function_name}();
""".strip()

    def _build_constraint_trigger_sql(
        self,
        trigger_name: str,
        table_name: str,
        function_name: str,
    ) -> str:
        return f"""
DROP TRIGGER IF EXISTS {trigger_name} ON {table_name};
CREATE CONSTRAINT TRIGGER {trigger_name}
AFTER INSERT OR UPDATE OR DELETE ON {table_name}
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION {function_name}();
""".strip()

    def _emit_bool_expr_for_trigger(self, expr: BoolExpr) -> str:
        if isinstance(expr, AndExpr):
            return f"({self._emit_bool_expr_for_trigger(expr.left)} AND {self._emit_bool_expr_for_trigger(expr.right)})"

        if isinstance(expr, OrExpr):
            return f"({self._emit_bool_expr_for_trigger(expr.left)} OR {self._emit_bool_expr_for_trigger(expr.right)})"

        if isinstance(expr, NotExpr):
            return f"(NOT {self._emit_bool_expr_for_trigger(expr.expr)})"

        if isinstance(expr, CompareExpr):
            return f"({self._emit_expr_for_trigger(expr.left)} {expr.operator} {self._emit_expr_for_trigger(expr.right)})"

        if isinstance(expr, IsNullExpr):
            suffix = "IS NOT NULL" if expr.negated else "IS NULL"
            return f"({self._emit_expr_for_trigger(expr.expr)} {suffix})"

        if isinstance(expr, BetweenExpr):
            keyword = "NOT BETWEEN" if expr.negated else "BETWEEN"
            return (
                f"({self._emit_expr_for_trigger(expr.value)} {keyword} "
                f"{self._emit_expr_for_trigger(expr.lower)} AND {self._emit_expr_for_trigger(expr.upper)})"
            )

        if isinstance(expr, InExpr):
            keyword = "NOT IN" if expr.negated else "IN"
            options_sql = ", ".join(self._emit_expr_for_trigger(opt) for opt in expr.options)
            return f"({self._emit_expr_for_trigger(expr.value)} {keyword} ({options_sql}))"

        if isinstance(expr, LikeExpr):
            value_sql = self._emit_expr_for_trigger(expr.value)
            pattern_sql = self._emit_expr_for_trigger(expr.pattern)

            keyword = "ILIKE" if expr.case_insensitive else "LIKE"
            if expr.negated:
                keyword = f"NOT {keyword}"

            return f"({value_sql} {keyword} {pattern_sql})"

        if isinstance(expr, BoolLiteralExpr):
            if expr.value is True:
                return "TRUE"
            if expr.value is False:
                return "FALSE"
            return "NULL"

        if isinstance(expr, IsBoolExpr):
            inner = self._emit_expr_for_trigger(expr.expr)
            keyword = f"IS {expr.check_for}"
            if expr.negated:
                keyword = f"IS NOT {expr.check_for}"
            return f"({inner} {keyword})"

        raise TypeError(f"Unsupported BoolExpr: {type(expr).__name__}")


    def _emit_expr_for_trigger(self, expr: Expr) -> str:
        if isinstance(expr, ColumnExpr):
            return expr.trigger_reference

        if isinstance(expr, LiteralExpr):
            return self._emit_literal(expr)

        if isinstance(expr, BinaryValueExpr):
            left_sql = self._emit_expr_for_trigger(expr.left)
            right_sql = self._emit_expr_for_trigger(expr.right)
            return f"({left_sql} {expr.operator} {right_sql})"

        if isinstance(expr, FunctionExpr):
            args_sql = ", ".join(self._emit_expr_for_trigger(arg) for arg in expr.args)
            return f"{expr.function_name}({args_sql})"

        if isinstance(expr, CastExpr):
            inner = self._emit_expr_for_trigger(expr.expr)
            if expr.use_pg_style:
                return f"({inner}::{expr.target_type})"
            return f"CAST({inner} AS {expr.target_type})"

        if isinstance(expr, BoolLiteralExpr):
            if expr.value is True:
                return "TRUE"
            if expr.value is False:
                return "FALSE"
            return "NULL"

        if isinstance(expr, UnaryValueExpr):
            inner = self._emit_expr_for_trigger(expr.expr)
            return f"({expr.operator}{inner})"

        raise TypeError(f"Unsupported Expr: {type(expr).__name__}")


    def _emit_literal(self, expr: LiteralExpr) -> str:
        if expr.literal_type == LiteralType.NULL:
            return "NULL"

        if expr.literal_type == LiteralType.BOOLEAN:
            return "TRUE" if expr.value else "FALSE"

        if expr.literal_type == LiteralType.NUMBER:
            return str(expr.value)

        if expr.literal_type == LiteralType.STRING:
            escaped = str(expr.value).replace("'", "''").replace("%", "%%")
            return f"'{escaped}'"

        raise ValueError(f"Unsupported literal type: {expr.literal_type}")

    def _emit_violation_condition_for_global_query(self, expr: ExistsExpr) -> str:
        query = expr.query_sql.strip().rstrip(";")

        if expr.negated:
            # Original: CHECK NOT EXISTS (Q)
            # Violation: EXISTS (Q)
            return f"EXISTS ({query})"

        # Original: CHECK EXISTS (Q)
        # Violation: NOT EXISTS (Q)
        return f"NOT EXISTS ({query})"