from compiler.contracts import (
    TestCaseResult,
    ValidationResult,
    TruthValue,
    SqlTestCaseResult
)

class CheckValidator:
    def __init__(self, evaluator, test_case_generator):
        self.evaluator = evaluator
        self.test_case_generator = test_case_generator

    def validate(self, request, engine=None) -> ValidationResult:
        errors = []
        results = []

        test_cases = self.test_case_generator.generate(request.constraint)

        for case in test_cases:
            actual_truth = self.evaluator.evaluate(request.constraint.condition, case.row)

            expected_truth = case.expected_truth
            expected_pass = self._passes_check(expected_truth)
            actual_pass = self._passes_check(actual_truth)

            execution_message = "Dry-run only."

            results.append(
                TestCaseResult(
                    row=case.row,
                    expected_truth=expected_truth,
                    actual_truth=actual_truth,
                    expected_pass=expected_pass,
                    actual_pass=actual_pass,
                    rationale=case.rationale,
                    execution_message=execution_message,
                )
            )

        success = len(errors) == 0 and all(
            r.expected_pass == r.actual_pass for r in results
        )

        summary = f"Validated {len(results)} test cases. Success={success}."

        return ValidationResult(
            success=success,
            test_case_results=results,
            errors=errors,
            summary=summary,
        )

    def _passes_check(self, truth_value: TruthValue) -> bool:
        return truth_value != TruthValue.FALSE

    def validate_exists_constraint(self, constraint, artifacts, db_conn) -> ValidationResult:
        create_table_sql = self.generate_create_table_sql(constraint)  # Replace with create sql from input/parser
        test_cases = self.generate_exists_test_cases(constraint)

        errors = []
        sql_test_case_results = []

        try:
            db_conn.execute(create_table_sql)
            db_conn.execute(artifacts.combined_sql)
            db_conn.connection.commit()
        except Exception as e:
            try:
                db_conn.connection.rollback()
            except Exception:
                pass

            return ValidationResult(
                success=False,
                test_case_results=[],
                sql_test_case_results=[],
                errors=[f"Failed to install schema/artifacts: {e}"],
                summary="Installation failed",
            )

        for case in test_cases:
            actual_pass = False
            execution_message = ""

            try:
                db_conn.execute(f"TRUNCATE {constraint.table_name} RESTART IDENTITY CASCADE;")
                db_conn.connection.commit()

                for stmt in case.setup_sql:
                    db_conn.execute(stmt)
                db_conn.connection.commit()

                for stmt in case.candidate_sql:
                    db_conn.execute(stmt)

                db_conn.connection.commit()

                actual_pass = True
                execution_message = "Committed successfully"

            except Exception as e:
                actual_pass = False
                execution_message = str(e)

                try:
                    db_conn.connection.rollback()
                except Exception:
                    pass

            sql_test_case_results.append(
                SqlTestCaseResult(
                    name=case.name,
                    expected_pass=case.expected_pass,
                    actual_pass=actual_pass,
                    rationale=case.rationale,
                    execution_message=execution_message,
                )
            )

        success = all(r.expected_pass == r.actual_pass for r in sql_test_case_results)

        return ValidationResult(
            success=success,
            test_case_results=[],
            sql_test_case_results=sql_test_case_results,
            errors=errors,
            summary=(
                f"{sum(r.expected_pass == r.actual_pass for r in sql_test_case_results)}"
                f"/{len(sql_test_case_results)} EXISTS test cases passed"
            ),
        )