from compiler.contracts import (
    TestCaseResult,
    ValidationResult,
    TruthValue,
    SqlTestCaseResult,
)


class CheckValidator:
    def __init__(self, evaluator, test_case_generator):
        self.evaluator = evaluator
        self.test_case_generator = test_case_generator

    def validate(self, request, db_conn=None) -> ValidationResult:
        errors = []
        results = []

        test_cases = self.test_case_generator.generate(request.constraint)

        for case in test_cases:
            actual_truth = self.evaluator.evaluate(request.constraint.condition, case.row)

            expected_truth = case.expected_truth
            expected_pass = self._passes_check(expected_truth)
            actual_pass = self._passes_check(actual_truth)

            results.append(
                TestCaseResult(
                    row=case.row,
                    expected_truth=expected_truth,
                    actual_truth=actual_truth,
                    expected_pass=expected_pass,
                    actual_pass=actual_pass,
                    rationale=case.rationale,
                    execution_message="Dry-run only.",
                )
            )

        sql_test_case_results = []

        if db_conn is not None:
            try:
                create_table_sql = self.test_case_generator.generate_create_table_sql(request.constraint)
                sql_test_cases = self.test_case_generator.generate_sql_test_cases_from_row_expectations(
                    request.constraint,
                    test_cases,
                )

                sql_test_case_results = self._run_sql_test_cases(
                    constraint=request.constraint,
                    artifacts=request.artifacts,
                    create_table_sql=create_table_sql,
                    sql_test_cases=sql_test_cases,
                    db_conn=db_conn,
                )
            except Exception as e:
                errors.append(f"SQL validation failed: {e}")

        success = (
            len(errors) == 0
            and all(r.expected_pass == r.actual_pass for r in results)
            and all(r.expected_pass == r.actual_pass for r in sql_test_case_results)
        )

        summary = (
            f"Validated {len(results)} dry-run test cases"
            f" and {len(sql_test_case_results)} SQL test cases. Success={success}."
        )

        return ValidationResult(
            success=success,
            test_case_results=results,
            sql_test_case_results=sql_test_case_results,
            errors=errors,
            summary=summary,
        )

    def _passes_check(self, truth_value: TruthValue) -> bool:
        return truth_value != TruthValue.FALSE

    def validate_exists_constraint(self, constraint, artifacts, db_conn) -> ValidationResult:
        create_table_sql = self.test_case_generator.generate_create_table_sql(constraint)
        test_cases = self.test_case_generator.generate_exists_test_cases(constraint)

        errors = []

        try:
            sql_test_case_results = self._run_sql_test_cases(
                constraint=constraint,
                artifacts=artifacts,
                create_table_sql=create_table_sql,
                sql_test_cases=test_cases,
                db_conn=db_conn,
            )
        except Exception as e:
            return ValidationResult(
                success=False,
                test_case_results=[],
                sql_test_case_results=[],
                errors=[f"Failed to install schema/artifacts: {e}"],
                summary="Installation failed",
            )

        success = all(r.expected_pass == r.actual_pass for r in sql_test_case_results)
        summary = f"Validated {len(sql_test_case_results)} SQL test cases. Success={success}."

        return ValidationResult(
            success=success,
            test_case_results=[],
            sql_test_case_results=sql_test_case_results,
            errors=errors,
            summary=summary,
        )

    def _run_sql_test_cases(self, constraint, artifacts, create_table_sql, sql_test_cases, db_conn):
        sql_test_case_results = []

        db_conn.execute(create_table_sql)
        db_conn.execute(artifacts.combined_sql)
        db_conn.connection.commit()

        for case in sql_test_cases:
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

        return sql_test_case_results