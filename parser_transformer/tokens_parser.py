from compiler.contracts import (
    Token, Expr, BoolExpr, OrExpr, AndExpr, CompareExpr,
    ColumnExpr, LiteralExpr, LikeExpr, LiteralType, InExpr, CastExpr,
    BetweenExpr, IsNullExpr, BinaryValueExpr, UnaryValueExpr,
    BoolLiteralExpr, IsBoolExpr, ExistsExpr, NotExpr, FunctionExpr
)
from parser_transformer.transformer import tokenize
from parser_transformer.extractor import extract_parenthesized


class CheckExprParser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.index = 0

    def current(self) -> Token:
        return self.tokens[self.index]

    def advance(self) -> Token:
        tok = self.tokens[self.index]
        self.index += 1
        return tok

    def match(self, kind: str) -> bool:
        if self.current().kind == kind:
            self.index += 1
            return True
        return False

    def expect(self, kind: str) -> Token:
        tok = self.current()
        if tok.kind != kind:
            raise ValueError(f"Expected {kind}, got {tok.kind} at pos {tok.pos}")
        self.index += 1
        return tok

    @staticmethod
    def parse_check_expression(check_expr_sql: str) -> BoolExpr:
        stripped = check_expr_sql.strip()
        upper = stripped.upper()

        if upper.startswith("NOT EXISTS"):
            exists_idx = upper.find("EXISTS")
            open_idx = exists_idx + len("EXISTS")
            while open_idx < len(stripped) and stripped[open_idx].isspace():
                open_idx += 1
            if open_idx >= len(stripped) or stripped[open_idx] != "(":
                raise ValueError("Expected '(' after NOT EXISTS")
            query_sql, _ = extract_parenthesized(stripped, open_idx)
            return ExistsExpr(query_sql=query_sql.strip(), negated=True)

        if upper.startswith("EXISTS"):
            open_idx = upper.find("EXISTS") + len("EXISTS")
            while open_idx < len(stripped) and stripped[open_idx].isspace():
                open_idx += 1
            if open_idx >= len(stripped) or stripped[open_idx] != "(":
                raise ValueError("Expected '(' after EXISTS")
            query_sql, _ = extract_parenthesized(stripped, open_idx)
            return ExistsExpr(query_sql=query_sql.strip(), negated=False)

        return CheckExprParser(tokenize(stripped)).parse()

    def parse(self) -> BoolExpr:
        expr = self.parse_or()
        if self.current().kind != "EOF":
            tok = self.current()
            raise ValueError(f"Unexpected token {tok.value!r} at pos {tok.pos}")
        return expr

    def parse_or(self) -> BoolExpr:
        expr = self.parse_and()
        while self.match("OR"):
            expr = OrExpr(left=expr, right=self.parse_and())
        return expr

    def parse_and(self) -> BoolExpr:
        expr = self.parse_predicate()
        while self.match("AND"):
            expr = AndExpr(left=expr, right=self.parse_predicate())
        return expr

    def parse_predicate(self) -> Expr:
        if self.match("NOT"):
            return NotExpr(expr=self.parse_predicate())

        if self.match("LPAREN"):
            expr = self.parse_or()
            self.expect("RPAREN")
            return expr

        left = self.parse_value_expr()

        negated = self.match("NOT")

        if self.match("LIKE") or self.match("ILIKE"):
            op = self.tokens[self.index - 1]
            return LikeExpr(
                value=left,
                pattern=self.parse_value_expr(),
                negated=negated,
                case_insensitive=(op.kind == "ILIKE"),
            )

        if self.match("IN"):
            self.expect("LPAREN")
            options = [self.parse_value_expr()]
            while self.match("COMMA"):
                options.append(self.parse_value_expr())
            self.expect("RPAREN")
            return InExpr(value=left, options=options, negated=negated)

        if self.match("BETWEEN"):
            lower = self.parse_value_expr()
            self.expect("AND")
            upper = self.parse_value_expr()
            return BetweenExpr(value=left, lower=lower, upper=upper, negated=negated)

        if negated:
            raise ValueError(f"Unexpected NOT at pos {self.current().pos}")

        if self.match("IS"):
            negated = self.match("NOT")

            if self.match("NULL"):
                return IsNullExpr(expr=left, negated=negated)

            for kind in ("TRUE", "FALSE", "UNKNOWN"):
                if self.match(kind):
                    return IsBoolExpr(expr=left, check_for=kind, negated=negated)

            raise ValueError(
                f"Expected NULL, TRUE, FALSE, or UNKNOWN after IS at pos {self.current().pos}"
            )

        tok = self.current()
        if tok.kind == "OP" and tok.value in {"=", "!=", "<>", ">", "<", ">=", "<="}:
            op = self.advance().value
            return CompareExpr(left=left, operator=op, right=self.parse_value_expr())

        if isinstance(left, BoolExpr):
            return left

        raise ValueError(f"Expected predicate operator at pos {tok.pos}")

    def parse_type_name(self) -> str:
        tok = self.current()
        if tok.kind != "IDENT":
            raise ValueError(f"Expected type name at pos {tok.pos}, got {tok.kind}")
        self.advance()
        return tok.value.upper()

    def parse_value_expr(self) -> Expr:
        if self.current().kind == "OP" and self.current().value in {"+", "-"}:
            return UnaryValueExpr(operator=self.advance().value, expr=self.parse_value_expr())

        expr = self.parse_primary_value()

        while True:
            tok = self.current()

            if tok.kind == "OP" and tok.value == "::":
                self.advance()
                expr = CastExpr(
                    expr=expr,
                    target_type=self.parse_type_name(),
                    use_pg_style=True,
                )
                continue

            if tok.kind == "OP" and tok.value in {"+", "-"}:
                expr = BinaryValueExpr(
                    left=expr,
                    operator=self.advance().value,
                    right=self.parse_primary_value(),
                )
                continue

            break

        return expr

    def parse_primary_value(self) -> Expr:
        tok = self.current()

        if tok.kind == "IDENT":
            name = tok.value
            self.advance()

            if self.match("LPAREN"):
                args = []

                if not self.match("RPAREN"):
                    while True:
                        args.append(self.parse_value_expr())
                        if self.match("COMMA"):
                            continue
                        self.expect("RPAREN")
                        break

                return FunctionExpr(
                    function_name=name,
                    args=args,
                )

            return ColumnExpr(
                original_name=name,
                trigger_reference=f"NEW.{name}",
            )

        if tok.kind == "CAST":
            self.advance()
            self.expect("LPAREN")
            inner = self.parse_value_expr()
            self.expect("AS")
            target_type = self.parse_type_name()
            self.expect("RPAREN")
            return CastExpr(expr=inner, target_type=target_type, use_pg_style=False)

        if tok.kind == "NUMBER":
            self.advance()
            return LiteralExpr(float(tok.value), LiteralType.NUMBER) if "." in tok.value else LiteralExpr(int(tok.value), LiteralType.NUMBER)

        if tok.kind == "STRING":
            self.advance()
            return LiteralExpr(tok.value, LiteralType.STRING)

        if tok.kind == "TRUE":
            self.advance()
            return BoolLiteralExpr(True)

        if tok.kind == "FALSE":
            self.advance()
            return BoolLiteralExpr(False)

        if self.match("LPAREN"):
            expr = self.parse_value_expr()
            self.expect("RPAREN")
            return expr

        raise ValueError(f"Expected value at pos {tok.pos}, got {tok.kind}")