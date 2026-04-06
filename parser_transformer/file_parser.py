from util.log import log, LogTag

def split_sql_statements(sql_text: str) -> list[str]:
    statements = []
    current = []

    paren_depth = 0
    bracket_depth = 0

    in_single_quote = False
    in_double_quote = False

    i = 0
    n = len(sql_text)

    while i < n:
        ch = sql_text[i]

        # Inside single-quoted string
        if in_single_quote:
            current.append(ch)

            if ch == "'":
                if i + 1 < n and sql_text[i + 1] == "'":
                    current.append(sql_text[i + 1])
                    i += 2
                    continue
                else:
                    in_single_quote = False

            i += 1
            continue

        # Inside double-quoted identifier
        if in_double_quote:
            current.append(ch)

            if ch == '"':
                if i + 1 < n and sql_text[i + 1] == '"':
                    current.append(sql_text[i + 1])
                    i += 2
                    continue
                else:
                    in_double_quote = False

            i += 1
            continue

        # Enter quotes
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

        # Track nesting
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

        # Split on top-level semicolon only
        if ch == ";" and paren_depth == 0 and bracket_depth == 0:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue

        current.append(ch)
        i += 1

    # Flush trailing statement
    stmt = "".join(current).strip()
    
    if stmt:
        statements.append(stmt)

    if in_single_quote or in_double_quote:
        raise ValueError("Unterminated quote in SQL input")
    if paren_depth != 0 or bracket_depth != 0:
        raise ValueError("Unbalanced parentheses/brackets in SQL input")
    
    log(f"{len(statements)} statements loaded", LogTag.INFO)
    return statements
