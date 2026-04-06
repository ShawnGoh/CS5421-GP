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
                    expected_truth=TruthValue.UNKNOWN,
                    rationale="NULL IS TRUE is FALSE",
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

        return []

    def generate_create_table_sql(self, constraint):
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
                    right=LiteralExpr(True, LiteralType.BOOLEAN),
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
                    expr=CompareExpr(
                        left=ColumnExpr("is_active", "NEW.is_active"),
                        operator="=",
                        right=LiteralExpr(True, LiteralType.BOOLEAN),
                    ),
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