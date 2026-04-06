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
    BoolLiteralExpr
)

KEYWORDS = {
    "AND", "OR", "NOT", "IS", "NULL", "TRUE", "FALSE",
    "LIKE", "UNKNOWN", "IN", "BETWEEN",
    "CAST", "AS",
}

TWO_CHAR_OPS = {"::", ">=", "<=", "<>", "!="}
ONE_CHAR_OPS = {"=", ">", "<", "+", "-"}

unsupported = ["SELECT", "EXISTS", "FROM", "WHERE"]

def reject_unsupported_features(check_expr_sql: str) -> None:
    upper_sql = check_expr_sql.upper()

    for word in unsupported:
        if word in upper_sql:
            raise ValueError(
                f"Unsupported CHECK expression feature detected: {word}"
            )

def tokenize(text: str) -> list[Token]:
    i = 0
    max_pos = len(text)
    tokens: list[Token] = []

    while i < max_pos:
        ch = text[i]

        # 1. whitespace
        if ch.isspace():
            i += 1
            continue

        # 2. left paren
        if ch == "(":
            tokens.append(Token("LPAREN", ch, i))
            i += 1
            continue

        # 3. right paren
        if ch == ")":
            tokens.append(Token("RPAREN", ch, i))
            i += 1
            continue

        # 4. two-char operators
        if i + 1 < max_pos and text[i:i + 2] in TWO_CHAR_OPS:
            tokens.append(Token("OP", text[i:i + 2], i))
            i += 2
            continue

        # 5. one-char operators
        if ch in ONE_CHAR_OPS:
            tokens.append(Token("OP", ch, i))
            i += 1
            continue

        # 6. string literal
        if ch == "'":
            start = i
            i += 1
            chars = []

            while i < max_pos:
                if text[i] == "'":
                    if i + 1 < max_pos and text[i + 1] == "'":
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

        # 7. number
        if ch.isdigit():
            start = i
            saw_dot = False

            while i < max_pos and (text[i].isdigit() or (text[i] == "." and not saw_dot)):
                if text[i] == ".":
                    saw_dot = True
                i += 1

            tokens.append(Token("NUMBER", text[start:i], start))
            continue

        # 8. quoted identifier
        if ch == '"':
            start = i
            i += 1
            chars = []

            while i < max_pos:
                if text[i] == '"':
                    if i + 1 < max_pos and text[i + 1] == '"':
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

        # 9. bare identifier / keyword
        if ch.isalpha() or ch == "_":
            start = i
            i += 1

            while i < max_pos and (text[i].isalnum() or text[i] in {"_", "$"}):
                i += 1

            word = text[start:i]
            upper_word = word.upper()

            if upper_word in KEYWORDS:
                tokens.append(Token(upper_word, upper_word, start))
            else:
                tokens.append(Token("IDENT", word, start))
            continue
        
        if ch == ",":
            tokens.append(Token("COMMA", ",", i))
            i += 1
            continue
        
        # 10. unknown character
        raise ValueError(f"Unexpected character {ch!r} at position {i}")

    tokens.append(Token("EOF", "", max_pos))
    return tokens

def collect_referenced_columns(expr: Expr) -> list[str]:
    seen = set()
    ordered = []

    def add(name: str):
        if name not in seen:
            seen.add(name)
            ordered.append(name)

    def visit(node: Expr):
        match node:
            case ColumnExpr():
                add(node.original_name)

            case LiteralExpr():
                pass
            
            case BoolLiteralExpr():
                pass    

            case CompareExpr(left=left, right=right):
                visit(left)
                visit(right)

            case AndExpr(left=left, right=right):
                visit(left)
                visit(right)

            case OrExpr(left=left, right=right):
                visit(left)
                visit(right)

            case NotExpr(expr=expr):
                visit(expr)

            case IsNullExpr(expr=expr):
                visit(expr)

            case IsBoolExpr(expr=expr):
                visit(expr)

            case LikeExpr(value=value, pattern=pattern):
                visit(value)
                visit(pattern)

            case UnaryValueExpr(expr=expr):
                visit(expr)

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

            case CastExpr(expr=expr):
                visit(expr)

            case _:
                raise ValueError(
                    f"Unsupported node type in column collector: {type(node).__name__}"
                )

    visit(expr)
    return ordered