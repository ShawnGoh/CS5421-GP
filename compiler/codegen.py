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
        procedure_name = f"procedure_{constraint.table_name}_{constraint.constraint_name}"
        function_name = f"trigger_function_{constraint.table_name}_{constraint.constraint_name}"
        trigger_name = f"trigger_{constraint.table_name}_{constraint.constraint_name}"

        if isinstance(constraint.condition, ExistsExpr):
            procedure_sql = self._build_global_query_procedure_sql(constraint, procedure_name)
            function_sql = self._build_noarg_trigger_function_sql(procedure_name, function_name)
            trigger_sql = self._build_constraint_trigger_sql(
                trigger_name,
                constraint.table_name,
                function_name,
            )
        else:
            procedure_sql = self._build_procedure_sql(constraint, procedure_name)
            # condition_sql = self._emit_bool_expr(constraint.condition)
            function_sql = self._build_trigger_function_sql(constraint, procedure_name, function_name)
            trigger_sql = self._build_trigger_sql(trigger_name, constraint.table_name, function_name)

        combined_sql = procedure_sql + "\n\n" + function_sql + "\n\n" + trigger_sql

        return OutputCheck(
            procedure_name=procedure_name,
            function_name=function_name,
            trigger_name=trigger_name,
            procedure_sql=procedure_sql,
            function_sql=function_sql,
            trigger_sql=trigger_sql,
            combined_sql=combined_sql,
        )

    def _build_procedure_sql(self, constraint: TransformedCheckConstraint, procedure_name: str) -> str:
        params_sql = self._build_procedure_params(constraint.referenced_columns)
        condition_sql = self._emit_bool_expr_for_procedure(constraint.condition)
        escaped_message = constraint.original_check_sql.replace("'", "''")

        return f"""
CREATE OR REPLACE PROCEDURE {procedure_name}(
    {params_sql}
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF ({condition_sql}) IS FALSE THEN
        RAISE EXCEPTION 'CHECK constraint violated: {escaped_message}';
    END IF;
END;
$$;
""".strip()

    def _build_global_query_procedure_sql(self, constraint: TransformedCheckConstraint, procedure_name: str) -> str:
        if not isinstance(constraint.condition, ExistsExpr):
            raise TypeError(
                f"Global raw-query procedure expects ExistsExpr, got {type(constraint.condition).__name__}"
            )

        violation_condition = self._emit_violation_condition_for_global_query(constraint.condition)
        escaped_message = constraint.original_check_sql.replace("'", "''")

        return f"""
CREATE OR REPLACE PROCEDURE {procedure_name}()
LANGUAGE plpgsql
AS $$
BEGIN
    IF {violation_condition} THEN
        RAISE EXCEPTION 'CHECK constraint violated: {escaped_message}';
    END IF;
END;
$$;
""".strip()

    def _build_trigger_function_sql(
        self,
        constraint: TransformedCheckConstraint,
        procedure_name: str,
        function_name: str,
    ) -> str:
        call_args = self._build_trigger_call_args(constraint.referenced_columns)

        return f"""
CREATE OR REPLACE FUNCTION {function_name}()
RETURNS TRIGGER AS $$
BEGIN
    CALL {procedure_name}(
        {call_args}
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""".strip()

    def _build_noarg_trigger_function_sql(
        self,
        procedure_name: str,
        function_name: str,
    ) -> str:
        return f"""
CREATE OR REPLACE FUNCTION {function_name}()
RETURNS TRIGGER AS $$
BEGIN
    CALL {procedure_name}();
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

    def _build_procedure_params(self, referenced_columns: list[str]) -> str:
        params = [f"p_{col} {col_type}" for col, col_type in referenced_columns]
        return ",\n    ".join(params)

    def _build_trigger_call_args(self, referenced_columns: list[str]) -> str:
        return ",\n        ".join(f"NEW.{col[0]}" for col in referenced_columns)

    def _emit_bool_expr_for_procedure(self, expr: BoolExpr) -> str:
        if isinstance(expr, AndExpr):
            return f"({self._emit_bool_expr_for_procedure(expr.left)} AND {self._emit_bool_expr_for_procedure(expr.right)})"

        if isinstance(expr, OrExpr):
            return f"({self._emit_bool_expr_for_procedure(expr.left)} OR {self._emit_bool_expr_for_procedure(expr.right)})"

        if isinstance(expr, NotExpr):
            return f"(NOT {self._emit_bool_expr_for_procedure(expr.expr)})"

        if isinstance(expr, CompareExpr):
            return f"({self._emit_expr_for_procedure(expr.left)} {expr.operator} {self._emit_expr_for_procedure(expr.right)})"

        if isinstance(expr, IsNullExpr):
            suffix = "IS NOT NULL" if expr.negated else "IS NULL"
            return f"({self._emit_expr_for_procedure(expr.expr)} {suffix})"

        if isinstance(expr, BetweenExpr):
            keyword = "NOT BETWEEN" if expr.negated else "BETWEEN"
            return (
                f"({self._emit_expr_for_procedure(expr.value)} {keyword} "
                f"{self._emit_expr_for_procedure(expr.lower)} AND {self._emit_expr_for_procedure(expr.upper)})"
            )

        if isinstance(expr, InExpr):
            keyword = "NOT IN" if expr.negated else "IN"
            options_sql = ", ".join(self._emit_expr_for_procedure(opt) for opt in expr.options)
            return f"({self._emit_expr_for_procedure(expr.value)} {keyword} ({options_sql}))"

        if isinstance(expr, UnaryValueExpr):
            inner = self._emit_expr_for_procedure(expr.expr)
            return f"({expr.operator}{inner})"

        if isinstance(expr, LikeExpr):
            value_sql = self._emit_expr_for_procedure(expr.value)
            pattern_sql = self._emit_expr_for_procedure(expr.pattern)

            if expr.case_insensitive:
                keyword = "ILIKE"
            else:
                keyword = "LIKE"

            if expr.negated:
                keyword = f"NOT {keyword}"

            return f"({value_sql} {keyword} {pattern_sql})"

        if isinstance(expr, BoolLiteralExpr):
            if expr.value:
                return "TRUE"
            if expr.value is False:
                return "FALSE"
            return "NULL"

        if isinstance(expr, IsBoolExpr):
            inner = self._emit_bool_expr_for_procedure(expr.expr)
            keyword = f"IS {expr.check_for}"
            if expr.negated:
                keyword = f"IS NOT {expr.check_for}"
            return f"({inner} {keyword})"

        raise TypeError(f"Unsupported BoolExpr: {type(expr).__name__}")

    def _emit_expr_for_procedure(self, expr: Expr) -> str:
        if isinstance(expr, ColumnExpr):
            return f"p_{expr.original_name}"

        if isinstance(expr, LiteralExpr):
            return self._emit_literal(expr)
        
        if isinstance(expr, BinaryValueExpr):
            left_sql = self._emit_expr_for_procedure(expr.left)
            right_sql = self._emit_expr_for_procedure(expr.right)
            return f"({left_sql} {expr.operator} {right_sql})"

        if isinstance(expr, FunctionExpr):
            args_sql = ", ".join(self._emit_expr_for_procedure(arg) for arg in expr.args)
            return f"{expr.function_name}({args_sql})"

        if isinstance(expr, CastExpr):
            inner = self._emit_expr_for_procedure(expr.expr)

            if expr.use_pg_style:
                return f"({inner}::{expr.target_type})"
            else:
                return f"CAST({inner} AS {expr.target_type})"

        raise TypeError(f"Unsupported Expr: {type(expr).__name__}")

    def _emit_literal(self, expr: LiteralExpr) -> str:
        if expr.literal_type == LiteralType.NULL:
            return "NULL"

        if expr.literal_type == LiteralType.BOOLEAN:
            return "TRUE" if expr.value else "FALSE"

        if expr.literal_type == LiteralType.NUMBER:
            return str(expr.value)

        if expr.literal_type == LiteralType.STRING:
            escaped = str(expr.value).replace("'", "''")
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