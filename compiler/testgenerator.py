from contracts import TestRow, TestRowExpectation, TruthValue

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