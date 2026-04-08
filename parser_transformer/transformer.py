from compiler.contracts import (
    Expr,
    ColumnExpr,
    LiteralExpr,
    CompareExpr,
    AndExpr,
    OrExpr,
    NotExpr,
    IsNullExpr,
    IsBoolExpr,
    LikeExpr,
    UnaryValueExpr,
    BinaryValueExpr,
    FunctionExpr,
    BetweenExpr,
    InExpr,
    CastExpr,
    Token,
    BoolLiteralExpr,
    ExistsExpr,
)

KEYWORDS = {
    "AND", "OR", "NOT", "IS", "NULL", "TRUE", "FALSE",
    "LIKE", "ILIKE", "UNKNOWN", "IN", "BETWEEN",
    "CAST", "AS", "EXISTS",
}

MULTI_CHAR_OPS = {"::", ">=", "<=", "<>", "!="}
ONE_CHAR_OPS = {"=", ">", "<", "+", "-"}

UNSUPPORTED = set()


def reject_unsupported_features(check_expr_sql: str) -> None:
    upper_sql = check_expr_sql.upper()
    for word in UNSUPPORTED:
        if word in upper_sql:
            raise ValueError(f"Unsupported CHECK expression feature detected: {word}")


def tokenize(text: str) -> list[Token]:
    i = 0
    n = len(text)
    tokens: list[Token] = []

    while i < n:
        ch = text[i]

        if ch.isspace():
            i += 1
            continue

        if ch == "(":
            tokens.append(Token("LPAREN", ch, i))
            i += 1
            continue

        if ch == ")":
            tokens.append(Token("RPAREN", ch, i))
            i += 1
            continue

        if ch == ",":
            tokens.append(Token("COMMA", ch, i))
            i += 1
            continue

        if i + 1 < n and text[i:i + 2] in MULTI_CHAR_OPS:
            tokens.append(Token("OP", text[i:i + 2], i))
            i += 2
            continue

        if ch in ONE_CHAR_OPS:
            tokens.append(Token("OP", ch, i))
            i += 1
            continue

        if ch == "'":
            start = i
            i += 1
            chars = []

            while i < n:
                if text[i] == "'":
                    if i + 1 < n and text[i + 1] == "'":
                        chars.append("'")
                        i += 2
                        continue
                    i += 1
                    break
                chars.append(text[i])
                i += 1
            else:
                raise ValueError(f"Unterminated string literal at position {start}")

            tokens.append(Token("STRING", "".join(chars), start))
            continue

        if ch.isdigit():
            start = i
            saw_dot = False

            while i < n and (text[i].isdigit() or (text[i] == "." and not saw_dot)):
                if text[i] == ".":
                    saw_dot = True
                i += 1

            tokens.append(Token("NUMBER", text[start:i], start))
            continue

        if ch == '"':
            start = i
            i += 1
            chars = []

            while i < n:
                if text[i] == '"':
                    if i + 1 < n and text[i + 1] == '"':
                        chars.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                chars.append(text[i])
                i += 1
            else:
                raise ValueError(f"Unterminated quoted identifier at position {start}")

            tokens.append(Token("IDENT", "".join(chars), start))
            continue

        if ch.isalpha() or ch == "_":
            start = i
            i += 1

            while i < n and (text[i].isalnum() or text[i] in {"_", "$"}):
                i += 1

            word = text[start:i]
            upper_word = word.upper()
            kind = upper_word if upper_word in KEYWORDS else "IDENT"
            value = upper_word if kind != "IDENT" else word
            tokens.append(Token(kind, value, start))
            continue

        raise ValueError(f"Unexpected character {ch!r} at position {i}")

    tokens.append(Token("EOF", "", n))
    return tokens


def collect_referenced_columns(expr: Expr) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(name: str) -> None:
        if name not in seen:
            seen.add(name)
            ordered.append(name)

    def visit(node: Expr) -> None:
        match node:
            case ColumnExpr():
                add(node.original_name)

            case LiteralExpr() | BoolLiteralExpr() | ExistsExpr():
                return

            case CompareExpr(left=left, right=right):
                visit(left)
                visit(right)

            case AndExpr(left=left, right=right) | OrExpr(left=left, right=right):
                visit(left)
                visit(right)

            case NotExpr(expr=inner) | IsNullExpr(expr=inner) | IsBoolExpr(expr=inner) | UnaryValueExpr(expr=inner) | CastExpr(expr=inner):
                visit(inner)

            case LikeExpr(value=value, pattern=pattern):
                visit(value)
                visit(pattern)

            case BinaryValueExpr(left=left, right=right):
                visit(left)
                visit(right)

            case FunctionExpr(args=args):
                for arg in args:
                    visit(arg)

            case BetweenExpr(value=value, lower=lower, upper=upper):
                visit(value)
                visit(lower)
                visit(upper)

            case InExpr(value=value, options=options):
                visit(value)
                for opt in options:
                    visit(opt)

            case _:
                raise ValueError(
                    f"Unsupported node type in column collector: {type(node).__name__}"
                )

    visit(expr)
    return ordered