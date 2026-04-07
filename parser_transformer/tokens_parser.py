from compiler.contracts import (
    Token, Expr, BoolExpr, OrExpr, AndExpr, CompareExpr,
    ColumnExpr, LiteralExpr, LikeExpr, LiteralType, InExpr, CastExpr, 
    BetweenExpr, IsNullExpr, BinaryValueExpr, UnaryValueExpr, BoolLiteralExpr, IsBoolExpr, ExistsExpr
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

    def parse(self) -> BoolExpr:
        expr = self.parse_or()

        if self.current().kind != "EOF":
            tok = self.current()
            raise ValueError(f"Unexpected token {tok.value!r} at pos {tok.pos}")

        return expr

    def parse_or(self) -> BoolExpr:
        expr = self.parse_and()

        while self.match("OR"):
            right = self.parse_and()
            expr = OrExpr(left=expr, right=right)

        return expr

    def parse_and(self) -> BoolExpr:
        expr = self.parse_predicate()

        while self.match("AND"):
            right = self.parse_predicate()
            expr = AndExpr(left=expr, right=right)

        return expr

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

            return ExistsExpr(
                query_sql=query_sql.strip(),
                negated=True,
            )

        if upper.startswith("EXISTS"):
            open_idx = upper.find("EXISTS") + len("EXISTS")

            while open_idx < len(stripped) and stripped[open_idx].isspace():
                open_idx += 1

            if open_idx >= len(stripped) or stripped[open_idx] != "(":
                raise ValueError("Expected '(' after EXISTS")

            query_sql, _ = extract_parenthesized(stripped, open_idx)

            return ExistsExpr(
                query_sql=query_sql.strip(),
                negated=False,
            )

        # fallback to normal parser
        tokens = tokenize(stripped)
        parser = CheckExprParser(tokens)
        return parser.parse()
    
    
    def collect_parenthesized_raw_sql(self) -> str:
        self.expect("LPAREN")

        depth = 1
        pieces = []

        while True:
            tok = self.current()

            if tok.kind == "EOF":
                raise ValueError("Unterminated EXISTS subquery")

            if tok.kind == "LPAREN":
                depth += 1
                pieces.append(tok.value)
                self.advance()
                continue

            if tok.kind == "RPAREN":
                depth -= 1
                if depth == 0:
                    self.advance()
                    break
                pieces.append(tok.value)
                self.advance()
                continue

            pieces.append(tok.value)
            self.advance()

        return " ".join(pieces).strip()

    def parse_predicate(self) -> BoolExpr:
        if self.match("LPAREN"):
            expr = self.parse_or()
            self.expect("RPAREN")
            return expr

        left = self.parse_value_expr()

        if self.match("LIKE"):
            right = self.parse_value_expr()
            return LikeExpr(
                value=left,
                pattern=right,
                negated=False,
                case_insensitive=False,
            )

        if self.match("IN"):
            self.expect("LPAREN")
            options = []

            while True:
                option = self.parse_value_expr()
                options.append(option)

                if self.match("COMMA"):
                    continue
                break

            self.expect("RPAREN")

            return InExpr(
                value=left,
                options=options,
                negated=False,
            )

        if self.match("BETWEEN"):
            lower = self.parse_value_expr()
            self.expect("AND")
            upper = self.parse_value_expr()

            return BetweenExpr(
                value=left,
                lower=lower,
                upper=upper,
                negated=False,
            )

        if self.match("IS"):
            negated = self.match("NOT")

            if self.match("NULL"):
                return IsNullExpr(
                    expr=left,
                    negated=negated,
                )

            if self.match("TRUE"):
                return IsBoolExpr(
                    expr=left,
                    check_for="TRUE",
                    negated=negated,
                )

            if self.match("FALSE"):
                return IsBoolExpr(
                    expr=left,
                    check_for="FALSE",
                    negated=negated,
                )

            if self.match("UNKNOWN"):
                return IsBoolExpr(
                    expr=left,
                    check_for="UNKNOWN",
                    negated=negated,
                )

            raise ValueError(
                f"Expected NULL, TRUE, FALSE, or UNKNOWN after IS at pos {self.current().pos}"
            )

        tok = self.current()
        if tok.kind == "OP" and tok.value in {"=", "!=", "<>", ">", "<", ">=", "<="}:
            op = self.advance().value
            right = self.parse_value_expr()
            return CompareExpr(left=left, operator=op, right=right)
        
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
        expr = self.parse_primary_value()

        while True:
            tok = self.current()

            # postfix cast: expr::TYPE
            if tok.kind == "OP" and tok.value == "::":
                self.advance()
                target_type = self.parse_type_name()
                expr = CastExpr(
                    expr=expr,
                    target_type=target_type,
                    use_pg_style=True,
                )
                continue

            # binary arithmetic
            if tok.kind == "OP" and tok.value in {"+", "-"}:
                op = self.advance().value
                right = self.parse_primary_value()
                expr = BinaryValueExpr(
                    left=expr,
                    operator=op,
                    right=right,
                )
                continue

            break

        return expr
    
    def parse_primary_value(self) -> Expr:
        tok = self.current()

        if tok.kind == "IDENT":
            self.advance()
            return ColumnExpr(
                original_name=tok.value,
                trigger_reference=f"NEW.{tok.value}",
            )
            
        if tok.kind == "CAST":
            self.advance()
            self.expect("LPAREN")
            inner_expr = self.parse_value_expr()
            self.expect("AS")
            target_type = self.parse_type_name()
            self.expect("RPAREN")

            return CastExpr(
                expr=inner_expr,
                target_type=target_type,
                use_pg_style=False,
            )

        if tok.kind == "NUMBER":
            self.advance()
            if "." in tok.value:
                return LiteralExpr(float(tok.value), LiteralType.NUMBER)
            return LiteralExpr(int(tok.value), LiteralType.NUMBER)

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