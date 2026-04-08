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
    OutputCheck,
    UnaryValueExpr,
    TransformedCheckConstraint,
    TestRow, 
    TestRowExpectation, 
    TransformedCheckConstraint,
    TruthValue, 
    SqlTestCase
)

class TestCaseGenerator:
    def generate(self, constraint):
        name = constraint.constraint_name

        if name == "chk_price":
            return [
                TestRowExpectation(
                    row=TestRow({"price": 150, "discounted_price": 10}),
                    expected_truth=TruthValue.TRUE,
                    rationale="price > 100 and discounted_price > 0",
                ),
                TestRowExpectation(
                    row=TestRow({"price": 150, "discounted_price": 0}),
                    expected_truth=TruthValue.FALSE,
                    rationale="discounted_price > 0 is false",
                ),
                TestRowExpectation(
                    row=TestRow({"price": 80, "discounted_price": None}),
                    expected_truth=TruthValue.TRUE,
                    rationale="price <= 100 makes overall expression true",
                ),
            ]

        if name == "chk_products":
            return [
                TestRowExpectation(
                    row=TestRow({
                        "price": 50,
                        "status": "ACTIVE",
                        "discounted_price": 20,
                    }),
                    expected_truth=TruthValue.TRUE,
                    rationale="price in range, status allowed, discounted_price is not null",
                ),
                TestRowExpectation(
                    row=TestRow({
                        "price": 10,
                        "status": "PENDING",
                        "discounted_price": 0,
                    }),
                    expected_truth=TruthValue.TRUE,
                    rationale="boundary value 10 is included in BETWEEN; status allowed; discounted_price not null",
                ),
                TestRowExpectation(
                    row=TestRow({
                        "price": 100,
                        "status": "ACTIVE",
                        "discounted_price": 1,
                    }),
                    expected_truth=TruthValue.TRUE,
                    rationale="boundary value 100 is included in BETWEEN; status allowed; discounted_price not null",
                ),
                TestRowExpectation(
                    row=TestRow({
                        "price": 5,
                        "status": "ACTIVE",
                        "discounted_price": 20,
                    }),
                    expected_truth=TruthValue.FALSE,
                    rationale="price below lower bound makes BETWEEN false",
                ),
                TestRowExpectation(
                    row=TestRow({
                        "price": 150,
                        "status": "ACTIVE",
                        "discounted_price": 20,
                    }),
                    expected_truth=TruthValue.FALSE,
                    rationale="price above upper bound makes BETWEEN false",
                ),
                TestRowExpectation(
                    row=TestRow({
                        "price": 50,
                        "status": "INVALID",
                        "discounted_price": 20,
                    }),
                    expected_truth=TruthValue.FALSE,
                    rationale="status not in allowed set makes IN false",
                ),
                TestRowExpectation(
                    row=TestRow({
                        "price": 50,
                        "status": "ACTIVE",
                        "discounted_price": None,
                    }),
                    expected_truth=TruthValue.FALSE,
                    rationale="discounted_price IS NOT NULL is false when value is null",
                ),
                TestRowExpectation(
                    row=TestRow({
                        "price": None,
                        "status": "ACTIVE",
                        "discounted_price": 20,
                    }),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="BETWEEN with null price is UNKNOWN; TRUE AND TRUE with UNKNOWN gives UNKNOWN",
                ),
                TestRowExpectation(
                    row=TestRow({
                        "price": 50,
                        "status": None,
                        "discounted_price": 20,
                    }),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="IN with null status is UNKNOWN; TRUE AND TRUE with UNKNOWN gives UNKNOWN",
                ),
                TestRowExpectation(
                    row=TestRow({
                        "price": None,
                        "status": "INVALID",
                        "discounted_price": 20,
                    }),
                    expected_truth=TruthValue.FALSE,
                    rationale="UNKNOWN AND FALSE AND TRUE becomes FALSE because FALSE dominates AND",
                ),
                TestRowExpectation(
                    row=TestRow({
                        "price": None,
                        "status": None,
                        "discounted_price": 20,
                    }),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="UNKNOWN AND UNKNOWN AND TRUE remains UNKNOWN",
                ),
            ]

        if name == "chk_price_minus_discount":
            return [
                TestRowExpectation(
                    row=TestRow({"price": 100, "discount": 20}),
                    expected_truth=TruthValue.TRUE,
                    rationale="100 - 20 >= 0",
                ),
                TestRowExpectation(
                    row=TestRow({"price": 10, "discount": 20}),
                    expected_truth=TruthValue.FALSE,
                    rationale="10 - 20 < 0",
                ),
                TestRowExpectation(
                    row=TestRow({"price": None, "discount": 20}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="NULL arithmetic yields UNKNOWN, CHECK passes",
                ),
            ]

        if name == "chk_email_like":
            return [
                TestRowExpectation(
                    row=TestRow({"email": "user@gmail.com"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="matches gmail pattern",
                ),
                TestRowExpectation(
                    row=TestRow({"email": "user@yahoo.com"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="does not match gmail pattern",
                ),
                TestRowExpectation(
                    row=TestRow({"email": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="LIKE with NULL yields UNKNOWN, CHECK passes",
                ),
            ]

        if name == "chk_username_pattern_single_char":
            return [
                TestRowExpectation(
                    row=TestRow({"username": "abc"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="'abc' matches 'a_c' (_ matches exactly one char)",
                ),
                TestRowExpectation(
                    row=TestRow({"username": "axc"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="'axc' matches 'a_c'",
                ),
                TestRowExpectation(
                    row=TestRow({"username": "ac"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="missing middle char → does not match",
                ),
                TestRowExpectation(
                    row=TestRow({"username": "abbc"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="two chars between a and c → does not match '_'",
                ),
                TestRowExpectation(
                    row=TestRow({"username": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="LIKE with NULL yields UNKNOWN",
                ),
            ]

        if name == "chk_username_ilike":
            return [
                TestRowExpectation(
                    row=TestRow({"username": "admin123"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="matches prefix",
                ),
                TestRowExpectation(
                    row=TestRow({"username": "ADMIN123"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="ILIKE is case-insensitive",
                ),
                TestRowExpectation(
                    row=TestRow({"username": "AdMiNxyz"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="mixed case still matches",
                ),
                TestRowExpectation(
                    row=TestRow({"username": "useradmin"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="does not start with admin",
                ),
                TestRowExpectation(
                    row=TestRow({"username": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="ILIKE with NULL yields UNKNOWN",
                ),
            ]

        if name == "chk_username_ilike_single_char":
            return [
                TestRowExpectation(
                    row=TestRow({"username": "abc123"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="'abc123' matches 'a_c%'",
                ),
                TestRowExpectation(
                    row=TestRow({"username": "aXcXYZ"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="case-insensitive + single char match",
                ),
                TestRowExpectation(
                    row=TestRow({"username": "ac123"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="missing middle char",
                ),
                TestRowExpectation(
                    row=TestRow({"username": "abdc"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="two chars between a and c",
                ),
                TestRowExpectation(
                    row=TestRow({"username": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="ILIKE with NULL yields UNKNOWN",
                ),
            ]

        if name == "chk_true_literal":
            return [
                TestRowExpectation(
                    row=TestRow({}),
                    expected_truth=TruthValue.TRUE,
                    rationale="TRUE always passes",
                ),
            ]

        if name == "chk_is_active_true":
            return [
                TestRowExpectation(
                    row=TestRow({"is_active": True}),
                    expected_truth=TruthValue.TRUE,
                    rationale="TRUE = TRUE evaluates to TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"is_active": False}),
                    expected_truth=TruthValue.FALSE,
                    rationale="FALSE = TRUE evaluates to FALSE",
                ),
                TestRowExpectation(
                    row=TestRow({"is_active": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="NULL = TRUE evaluates to UNKNOWN under SQL semantics",
                ),
            ]

        if name == "chk_is_active_is_true":
            return [
                TestRowExpectation(
                    row=TestRow({"is_active": True}),
                    expected_truth=TruthValue.TRUE,
                    rationale="IS TRUE succeeds",
                ),
                TestRowExpectation(
                    row=TestRow({"is_active": False}),
                    expected_truth=TruthValue.FALSE,
                    rationale="IS TRUE fails",
                ),
                TestRowExpectation(
                    row=TestRow({"is_active": None}),
                    expected_truth=TruthValue.FALSE,
                    rationale="NULL IS TRUE evaluates to FALSE",
                ),
            ]

        if name == "chk_amount_cast_numeric":
            return [
                TestRowExpectation(
                    row=TestRow({"amount": "10"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="casts to 10.0 > 0",
                ),
                TestRowExpectation(
                    row=TestRow({"amount": "0"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="casts to 0.0, not > 0",
                ),
                TestRowExpectation(
                    row=TestRow({"amount": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="cast NULL -> UNKNOWN -> CHECK passes",
                ),
            ]

        if name == "chk_code_cast_text":
            return [
                TestRowExpectation(
                    row=TestRow({"code": 123}),
                    expected_truth=TruthValue.TRUE,
                    rationale="CAST(123 AS TEXT) becomes '123', and '123' <> '' is TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"code": 0}),
                    expected_truth=TruthValue.TRUE,
                    rationale="CAST(0 AS TEXT) becomes '0', and '0' <> '' is TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"code": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="CAST(NULL AS TEXT) is NULL, and NULL <> '' is UNKNOWN under SQL semantics",
                ),
            ]

        if name == "chk_not_banned":
            return [
                TestRowExpectation(
                    row=TestRow({"status": "ACTIVE"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="status = 'BANNED' is false, so NOT false is TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"status": "BANNED"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="status = 'BANNED' is true, so NOT true is FALSE",
                ),
                TestRowExpectation(
                    row=TestRow({"status": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="NULL comparison yields UNKNOWN, and NOT UNKNOWN remains UNKNOWN",
                ),
            ]

        if name == "chk_negative_test_val_allowed":
            return [
                TestRowExpectation(
                    row=TestRow({"test_val": 5}),
                    expected_truth=TruthValue.TRUE,
                    rationale="-5 <= 0 is TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"test_val": -3}),
                    expected_truth=TruthValue.FALSE,
                    rationale="3 <= 0 is FALSE",
                ),
                TestRowExpectation(
                    row=TestRow({"test_val": 0}),
                    expected_truth=TruthValue.TRUE,
                    rationale="-0 <= 0 is TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"test_val": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="unary minus on NULL yields NULL, comparison is UNKNOWN",
                ),
            ]

        if name == "chk_name_length":
            return [
                TestRowExpectation(
                    row=TestRow({"name": "Amy"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="length('Amy') = 3, so >= 3 is TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"name": "Al"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="length('Al') = 2, so >= 3 is FALSE",
                ),
                TestRowExpectation(
                    row=TestRow({"name": ""}),
                    expected_truth=TruthValue.FALSE,
                    rationale="length('') = 0, so >= 3 is FALSE",
                ),
                TestRowExpectation(
                    row=TestRow({"name": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="function on NULL yields NULL, comparison is UNKNOWN",
                ),
            ]

        if name == "chk_price_not_between":
            return [
                TestRowExpectation(
                    row=TestRow({"price": 5}),
                    expected_truth=TruthValue.TRUE,
                    rationale="5 is outside 10..100, so NOT BETWEEN is TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"price": 150}),
                    expected_truth=TruthValue.TRUE,
                    rationale="150 is outside 10..100, so NOT BETWEEN is TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"price": 10}),
                    expected_truth=TruthValue.FALSE,
                    rationale="10 is inside BETWEEN boundary, so NOT BETWEEN is FALSE",
                ),
                TestRowExpectation(
                    row=TestRow({"price": 50}),
                    expected_truth=TruthValue.FALSE,
                    rationale="50 is inside range, so NOT BETWEEN is FALSE",
                ),
                TestRowExpectation(
                    row=TestRow({"price": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="BETWEEN with NULL is UNKNOWN, so NOT BETWEEN is also UNKNOWN",
                ),
            ]

        if name == "chk_status_not_in":
            return [
                TestRowExpectation(
                    row=TestRow({"status": "ACTIVE"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="ACTIVE is not in forbidden set",
                ),
                TestRowExpectation(
                    row=TestRow({"status": "CANCELLED"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="CANCELLED is in forbidden set, so NOT IN is FALSE",
                ),
                TestRowExpectation(
                    row=TestRow({"status": "FAILED"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="FAILED is in forbidden set, so NOT IN is FALSE",
                ),
                TestRowExpectation(
                    row=TestRow({"status": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="NULL NOT IN (...) is UNKNOWN under SQL three-valued logic",
                ),
            ]

        if name == "chk_email_not_temp":
            return [
                TestRowExpectation(
                    row=TestRow({"email": "user@gmail.com"}),
                    expected_truth=TruthValue.TRUE,
                    rationale="does not match tempmail pattern, so NOT LIKE is TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"email": "x@tempmail.com"}),
                    expected_truth=TruthValue.FALSE,
                    rationale="matches tempmail pattern, so NOT LIKE is FALSE",
                ),
                TestRowExpectation(
                    row=TestRow({"email": None}),
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="LIKE with NULL is UNKNOWN, so NOT LIKE is UNKNOWN",
                ),
            ]

        if name == "chk_is_active_is_not_true":
            return [
                TestRowExpectation(
                    row=TestRow({"is_active": True}),
                    expected_truth=TruthValue.FALSE,
                    rationale="TRUE IS NOT TRUE is FALSE",
                ),
                TestRowExpectation(
                    row=TestRow({"is_active": False}),
                    expected_truth=TruthValue.TRUE,
                    rationale="FALSE IS NOT TRUE is TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"is_active": None}),
                    expected_truth=TruthValue.TRUE,
                    rationale="NULL IS NOT TRUE is TRUE",
                ),
            ]

        if name == "chk_discount_is_null":
            return [
                TestRowExpectation(
                    row=TestRow({"discount": None}),
                    expected_truth=TruthValue.TRUE,
                    rationale="discount IS NULL is TRUE",
                ),
                TestRowExpectation(
                    row=TestRow({"discount": 0}),
                    expected_truth=TruthValue.FALSE,
                    rationale="non-null value makes IS NULL false",
                ),
                TestRowExpectation(
                    row=TestRow({"discount": 5}),
                    expected_truth=TruthValue.FALSE,
                    rationale="non-null value makes IS NULL false",
                ),
            ]

        if name == "chk_false_literal":
            return [
                TestRowExpectation(
                    row=TestRow({}),
                    expected_truth=TruthValue.FALSE,
                    rationale="FALSE always fails",
                ),
            ]

        return []

    def generate_create_table_sql(self, constraint):
        if constraint.table_name == "products":
            return """
DROP TABLE IF EXISTS products CASCADE;

CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    price NUMERIC,
    discounted_price NUMERIC,
    discount NUMERIC,
    status TEXT,
    test_val NUMERIC
);
""".strip()

        if constraint.table_name == "orders":
            return """
DROP TABLE IF EXISTS orders CASCADE;
CREATE TABLE orders (
    status TEXT
);
""".strip()

        if constraint.table_name == "users":
            return """
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    name TEXT,
    email TEXT,
    username TEXT,
    status TEXT
);
""".strip()

        if constraint.table_name == "flags":
            return """
DROP TABLE IF EXISTS flags CASCADE;

CREATE TABLE flags (
    id BIGSERIAL PRIMARY KEY
);
""".strip()

        if constraint.table_name == "accounts":
            return """
DROP TABLE IF EXISTS accounts CASCADE;

CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    is_active BOOLEAN
);
""".strip()

        if constraint.table_name == "payments":
            return """
DROP TABLE IF EXISTS payments CASCADE;

CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    amount NUMERIC
);
""".strip()

        if constraint.table_name == "items":
            return """
DROP TABLE IF EXISTS items CASCADE;

CREATE TABLE items (
    id BIGSERIAL PRIMARY KEY,
    code NUMERIC
);
""".strip()

        if constraint.constraint_name == "fd_position_salary":
            return """
DROP TABLE IF EXISTS employees CASCADE;

CREATE TABLE employees (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    position TEXT NOT NULL,
    salary NUMERIC NOT NULL
);
""".strip()

        raise ValueError(f"No create table SQL configured for constraint: {constraint.constraint_name}")

    def generate_sql_test_cases_from_row_expectations(
        self,
        constraint,
        row_expectations) -> list[SqlTestCase]:
        table_name = constraint.table_name
        sql_test_cases = []

        for i, case in enumerate(row_expectations, start=1):
            columns = []
            values = []

            for col, value in case.row.values.items():
                columns.append(col)

                if value is None:
                    values.append("NULL")
                elif isinstance(value, bool):
                    values.append("TRUE" if value else "FALSE")
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                else:
                    escaped = str(value).replace("'", "''")
                    values.append(f"'{escaped}'")

            if not columns:
                insert_sql = f"INSERT INTO {constraint.table_name} DEFAULT VALUES"
            else:
                insert_sql = (
                    f"INSERT INTO {constraint.table_name} ({', '.join(columns)}) "
                    f"VALUES ({', '.join(values)})"
                )

            expected_pass = case.expected_truth != TruthValue.FALSE

            sql_test_cases.append(
                SqlTestCase(
                    name=f"{constraint.constraint_name}_row_case_{i}",
                    setup_sql=[],
                    candidate_sql=[insert_sql],
                    expected_pass=expected_pass,
                    rationale=case.rationale,
                )
            )

        return sql_test_cases

    def generate_exists_test_cases(self, constraint):
        name = constraint.constraint_name

        if name == "fd_position_salary":
            return [
                SqlTestCase(
                    name="empty_table",
                    setup_sql=[],
                    candidate_sql=[],
                    expected_pass=True,
                    rationale="Empty table has no violating pairs",
                ),
                SqlTestCase(
                    name="single_row",
                    setup_sql=[],
                    candidate_sql=[
                        "INSERT INTO employees (name, position, salary) VALUES ('Alice', 'Engineer', 5000)"
                    ],
                    expected_pass=True,
                    rationale="Single row cannot violate FD",
                ),
                SqlTestCase(
                    name="valid_same_salary",
                    setup_sql=[],
                    candidate_sql=[
                        "INSERT INTO employees (name, position, salary) VALUES ('Alice', 'Engineer', 5000)",
                        "INSERT INTO employees (name, position, salary) VALUES ('Bob', 'Engineer', 5000)",
                    ],
                    expected_pass=True,
                    rationale="Same position, same salary is valid",
                ),
                SqlTestCase(
                    name="invalid_different_salary",
                    setup_sql=[],
                    candidate_sql=[
                        "INSERT INTO employees (name, position, salary) VALUES ('Alice', 'Engineer', 5000)",
                        "INSERT INTO employees (name, position, salary) VALUES ('Bob', 'Engineer', 6000)",
                    ],
                    expected_pass=False,
                    rationale="Same position but different salary violates FD",
                ),
                SqlTestCase(
                    name="insert_after_valid_fails",
                    setup_sql=[
                        "INSERT INTO employees (name, position, salary) VALUES ('Alice', 'Engineer', 5000)",
                        "INSERT INTO employees (name, position, salary) VALUES ('Bob', 'Engineer', 5000)",
                    ],
                    candidate_sql=[
                        "INSERT INTO employees (name, position, salary) VALUES ('Carol', 'Engineer', 7000)"
                    ],
                    expected_pass=False,
                    rationale="New row introduces FD violation",
                ),
                SqlTestCase(
                    name="update_creates_violation",
                    setup_sql=[
                        "INSERT INTO employees (name, position, salary) VALUES ('Alice', 'Engineer', 5000)",
                        "INSERT INTO employees (name, position, salary) VALUES ('Bob', 'Engineer', 5000)",
                    ],
                    candidate_sql=[
                        "UPDATE employees SET salary = 7000 WHERE name = 'Bob'"
                    ],
                    expected_pass=False,
                    rationale="Update introduces FD violation",
                ),
                SqlTestCase(
                    name="update_same_value_pass",
                    setup_sql=[
                        "INSERT INTO employees (name, position, salary) VALUES ('Alice', 'Engineer', 5000)",
                        "INSERT INTO employees (name, position, salary) VALUES ('Bob', 'Engineer', 5000)",
                    ],
                    candidate_sql=[
                        "UPDATE employees SET salary = 5000 WHERE name = 'Bob'"
                    ],
                    expected_pass=True,
                    rationale="No change → still valid",
                ),
                SqlTestCase(
                    name="deferred_valid_transaction",
                    setup_sql=[
                        "INSERT INTO employees (name, position, salary) VALUES ('Alice', 'Engineer', 5000)",
                        "INSERT INTO employees (name, position, salary) VALUES ('Bob', 'Engineer', 5000)",
                    ],
                    candidate_sql=[
                        "UPDATE employees SET salary = 7000 WHERE name = 'Bob'",
                        "UPDATE employees SET salary = 7000 WHERE name = 'Alice'",
                    ],
                    expected_pass=True,
                    rationale="Final state valid, deferred trigger allows it",
                ),
                SqlTestCase(
                    name="deferred_invalid_transaction",
                    setup_sql=[
                        "INSERT INTO employees (name, position, salary) VALUES ('Alice', 'Engineer', 5000)",
                        "INSERT INTO employees (name, position, salary) VALUES ('Bob', 'Engineer', 5000)",
                    ],
                    candidate_sql=[
                        "UPDATE employees SET salary = 7000 WHERE name = 'Bob'"
                    ],
                    expected_pass=False,
                    rationale="Final state invalid → fails at commit",
                ),
                SqlTestCase(
                    name="delete_removes_violation",
                    setup_sql=[
                        "ALTER TABLE employees DISABLE TRIGGER trigger_employees_fd_position_salary",
                        "INSERT INTO employees (name, position, salary) VALUES ('Alice', 'Engineer', 5000)",
                        "INSERT INTO employees (name, position, salary) VALUES ('Bob', 'Engineer', 6000)",
                        "ALTER TABLE employees ENABLE TRIGGER trigger_employees_fd_position_salary",
                    ],
                    candidate_sql=[
                        "DELETE FROM employees WHERE name = 'Bob'"
                    ],
                    expected_pass=True,
                    rationale="Delete removes violation",
                ),
            ]

        return []

    def generate_constraints(self):
        constraints = []
        constraints.append(
            TransformedCheckConstraint(
                table_name="products",
                constraint_name="chk_price",
                condition=OrExpr(
                    left=AndExpr(
                        left=CompareExpr(
                            left=ColumnExpr("price", "NEW.price"),
                            operator=">",
                            right=LiteralExpr(100, LiteralType.NUMBER),
                        ),
                        right=CompareExpr(
                            left=ColumnExpr("discounted_price", "NEW.discounted_price"),
                            operator=">",
                            right=LiteralExpr(0, LiteralType.NUMBER),
                        ),
                    ),
                    right=CompareExpr(
                        left=ColumnExpr("price", "NEW.price"),
                        operator="<=",
                        right=LiteralExpr(100, LiteralType.NUMBER),
                    ),
                ),
                referenced_columns=[("price", "NUMERIC"), ("discounted_price", "NUMERIC")],
                original_check_sql="CHECK ((price > 100 AND discounted_price > 0) OR (price <= 100))",
            )
        )
        constraints.append(
            TransformedCheckConstraint(
                table_name="products",
                constraint_name="chk_products",
                condition=AndExpr(
                    left=AndExpr(
                        left=BetweenExpr(
                            value=ColumnExpr("price", "NEW.price"),
                            lower=LiteralExpr(10, LiteralType.NUMBER),
                            upper=LiteralExpr(100, LiteralType.NUMBER),
                        ),
                        right=InExpr(
                            value=ColumnExpr("status", "NEW.status"),
                            options=[
                                LiteralExpr("ACTIVE", LiteralType.STRING),
                                LiteralExpr("PENDING", LiteralType.STRING),
                            ],
                        ),
                    ),
                    right=IsNullExpr(
                        expr=ColumnExpr("discounted_price", "NEW.discounted_price"),
                        negated=True,
                    ),
                ),
                referenced_columns=[("price", "NUMERIC"), ("status", "TEXT"), ("discounted_price", "NUMERIC")],
                original_check_sql="CHECK (price BETWEEN 10 AND 100 AND status IN ('ACTIVE', 'PENDING') AND discounted_price IS NOT NULL)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="products",
                constraint_name="chk_price_minus_discount",
                condition=CompareExpr(
                    left=BinaryValueExpr(
                        left=ColumnExpr("price", "NEW.price"),
                        operator="-",
                        right=ColumnExpr("discount", "NEW.discount"),
                    ),
                    operator=">=",
                    right=LiteralExpr(0, LiteralType.NUMBER),
                ),
                referenced_columns=[("price", "NUMERIC"), ("discount", "NUMERIC")],
                original_check_sql="CHECK (price - discount >= 0)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="users",
                constraint_name="chk_email_like",
                condition=LikeExpr(
                    value=ColumnExpr("email", "NEW.email"),
                    pattern=LiteralExpr("%@gmail.com", LiteralType.STRING),
                    negated=False,
                    case_insensitive=False,
                ),
                referenced_columns=[("email", "TEXT")],
                original_check_sql="CHECK (email LIKE '%@gmail.com')",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="users",
                constraint_name="chk_username_pattern_single_char",
                condition=LikeExpr(
                    value=ColumnExpr("username", "NEW.username"),
                    pattern=LiteralExpr("a_c", LiteralType.STRING),
                    negated=False,
                    case_insensitive=False,
                ),
                referenced_columns=[("username", "TEXT")],
                original_check_sql="CHECK (username LIKE 'a_c')",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="users",
                constraint_name="chk_username_ilike",
                condition=LikeExpr(
                    value=ColumnExpr("username", "NEW.username"),
                    pattern=LiteralExpr("admin%", LiteralType.STRING),
                    negated=False,
                    case_insensitive=True,
                ),
                referenced_columns=[("username", "TEXT")],
                original_check_sql="CHECK (username ILIKE 'admin%')",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="users",
                constraint_name="chk_username_ilike_single_char",
                condition=LikeExpr(
                    value=ColumnExpr("username", "NEW.username"),
                    pattern=LiteralExpr("a_c%", LiteralType.STRING),
                    negated=False,
                    case_insensitive=True,
                ),
                referenced_columns=[("username", "TEXT")],
                original_check_sql="CHECK (username ILIKE 'a_c%')",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="flags",
                constraint_name="chk_true_literal",
                condition=BoolLiteralExpr(True),
                referenced_columns=[],
                original_check_sql="CHECK (TRUE)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="accounts",
                constraint_name="chk_is_active_true",
                condition=CompareExpr(
                    left=ColumnExpr("is_active", "NEW.is_active"),
                    operator="=",
                    right=BoolLiteralExpr(True),
                ),
                referenced_columns=[("is_active", "BOOLEAN")],
                original_check_sql="CHECK (is_active = TRUE)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="accounts",
                constraint_name="chk_is_active_is_true",
                condition=IsBoolExpr(
                    expr=ColumnExpr("is_active", "NEW.is_active"),
                    check_for="TRUE",
                    negated=False,
                ),
                referenced_columns=[("is_active", "BOOLEAN")],
                original_check_sql="CHECK (is_active IS TRUE)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="payments",
                constraint_name="chk_amount_cast_numeric",
                condition=CompareExpr(
                    left=CastExpr(
                        expr=ColumnExpr("amount", "NEW.amount"),
                        target_type="NUMERIC",
                        use_pg_style=True,
                    ),
                    operator=">",
                    right=LiteralExpr(0, LiteralType.NUMBER),
                ),
                referenced_columns=[("amount", "NUMERIC")],
                original_check_sql="CHECK (amount::numeric > 0)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="items",
                constraint_name="chk_code_cast_text",
                condition=CompareExpr(
                    left=CastExpr(
                        expr=ColumnExpr("code", "NEW.code"),
                        target_type="TEXT",
                        use_pg_style=False,
                    ),
                    operator="<>",
                    right=LiteralExpr("", LiteralType.STRING),
                ),
                referenced_columns=[("code", "NUMERIC")],
                original_check_sql="CHECK (CAST(code AS TEXT) <> '')",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="users",
                constraint_name="chk_not_banned",
                condition=NotExpr(
                    expr=CompareExpr(
                        left=ColumnExpr("status", "NEW.status"),
                        operator="=",
                        right=LiteralExpr("BANNED", LiteralType.STRING),
                    )
                ),
                referenced_columns=[("status", "TEXT")],
                original_check_sql="CHECK (NOT (status = 'BANNED'))",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="products",
                constraint_name="chk_negative_test_val_allowed",
                condition=CompareExpr(
                    left=UnaryValueExpr(
                        operator="-",
                        expr=ColumnExpr("test_val", "NEW.test_val"),
                    ),
                    operator="<=",
                    right=LiteralExpr(0, LiteralType.NUMBER),
                ),
                referenced_columns=[("test_val", "NUMERIC")],
                original_check_sql="CHECK (-test_val <= 0)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="users",
                constraint_name="chk_name_length",
                condition=CompareExpr(
                    left=FunctionExpr(
                        function_name="length",
                        args=[ColumnExpr("name", "NEW.name")],
                    ),
                    operator=">=",
                    right=LiteralExpr(3, LiteralType.NUMBER),
                ),
                referenced_columns=[("name", "TEXT")],
                original_check_sql="CHECK (length(name) >= 3)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="products",
                constraint_name="chk_price_not_between",
                condition=BetweenExpr(
                    value=ColumnExpr("price", "NEW.price"),
                    lower=LiteralExpr(10, LiteralType.NUMBER),
                    upper=LiteralExpr(100, LiteralType.NUMBER),
                    negated=True,
                ),
                referenced_columns=[("price", "NUMERIC")],
                original_check_sql="CHECK (price NOT BETWEEN 10 AND 100)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="orders",
                constraint_name="chk_status_not_in",
                condition=InExpr(
                    value=ColumnExpr("status", "NEW.status"),
                    options=[
                        LiteralExpr("CANCELLED", LiteralType.STRING),
                        LiteralExpr("FAILED", LiteralType.STRING),
                    ],
                    negated=True,
                ),
                referenced_columns=[("status", "TEXT")],
                original_check_sql="CHECK (status NOT IN ('CANCELLED', 'FAILED'))",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="users",
                constraint_name="chk_email_not_temp",
                condition=LikeExpr(
                    value=ColumnExpr("email", "NEW.email"),
                    pattern=LiteralExpr("%@tempmail.com", LiteralType.STRING),
                    negated=True,
                    case_insensitive=False,
                ),
                referenced_columns=[("email", "TEXT")],
                original_check_sql="CHECK (email NOT LIKE '%@tempmail.com')",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="users",
                constraint_name="chk_email_ilike",
                condition=LikeExpr(
                    value=ColumnExpr("email", "NEW.email"),
                    pattern=LiteralExpr("%@gmail.com", LiteralType.STRING),
                    negated=False,
                    case_insensitive=True,
                ),
                referenced_columns=[("email", "TEXT")],
                original_check_sql="CHECK (email ILIKE '%@gmail.com')",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="accounts",
                constraint_name="chk_is_active_is_not_true",
                condition=IsBoolExpr(
                    expr=ColumnExpr("is_active", "NEW.is_active"),
                    check_for="TRUE",
                    negated=True,
                ),
                referenced_columns=[("is_active", "BOOLEAN")],
                original_check_sql="CHECK (is_active IS NOT TRUE)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="products",
                constraint_name="chk_discount_is_null",
                condition=IsNullExpr(
                    expr=ColumnExpr("discount", "NEW.discount"),
                    negated=False,
                ),
                referenced_columns=[("discount", "NUMERIC")],
                original_check_sql="CHECK (discount IS NULL)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
                table_name="flags",
                constraint_name="chk_false_literal",
                condition=BoolLiteralExpr(False),
                referenced_columns=[],
                original_check_sql="CHECK (FALSE)",
            )
        )

        constraints.append(
            TransformedCheckConstraint(
            table_name="employees",
            constraint_name="fd_position_salary",
            condition=ExistsExpr(
                query_sql="""
SELECT *
FROM employees e1, employees e2
WHERE e1.position = e2.position
AND e1.salary <> e2.salary
""",
                negated=True,
            ),
            referenced_columns=[],
            original_check_sql="""
CHECK NOT EXISTS (
SELECT *
FROM employees e1, employees e2
WHERE e1.position = e2.position
    AND e1.salary <> e2.salary
)
""".strip(),
        ))

        return constraints