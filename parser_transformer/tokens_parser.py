from compiler.contracts import (
    Token, Expr, BoolExpr, OrExpr, AndExpr, CompareExpr,
    ColumnExpr, LiteralExpr, LikeExpr, LiteralType
)

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

    def parse_predicate(self) -> BoolExpr:
        if self.match("LPAREN"):
            expr = self.parse_or()
            self.expect("RPAREN")
            return expr

        left = self.parse_value()
        tok = self.current()

        if tok.kind == "LIKE":
            self.advance()
            right = self.parse_value()
            return LikeExpr(
                value=left,
                pattern=right,
                negated=False,
                case_insensitive=False,
            )

        if tok.kind == "ILIKE":
            self.advance()
            right = self.parse_value()
            return LikeExpr(
                value=left,
                pattern=right,
                negated=False,
                case_insensitive=True,
            )

        if tok.kind == "OP" and tok.value in {"=", "!=", "<>", ">", "<", ">=", "<="}:
            op = self.advance().value
            right = self.parse_value()
            return CompareExpr(left=left, operator=op, right=right)

        raise ValueError(f"Expected predicate operator at pos {tok.pos}")

    def parse_value(self) -> Expr:
        tok = self.current()

        if tok.kind == "IDENT":
            self.advance()
            return ColumnExpr(
                original_name=tok.value,
                trigger_reference=f"NEW.{tok.value}",
            )

        if tok.kind == "NUMBER":
            self.advance()
            if "." in tok.value:
                return LiteralExpr(float(tok.value), LiteralType.NUMBER)
            return LiteralExpr(int(tok.value), LiteralType.NUMBER)

        if tok.kind == "STRING":
            self.advance()
            return LiteralExpr(tok.value, LiteralType.STRING)

        raise ValueError(f"Expected value at pos {tok.pos}, got {tok.kind}")