from contracts import (
    TestCaseResult,
    ValidationResult,
    TruthValue,
)

class ConstraintValidator:
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