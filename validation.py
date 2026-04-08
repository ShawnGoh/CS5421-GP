from lib.client import db_session
from compiler.codegen import CheckCodeGenerator
from compiler.validator import CheckValidator
from compiler.contracts import ExistsExpr
from compiler.evaluator import ConstraintSemanticEvaluator
from compiler.testgenerator import TestCaseGenerator
from util.log import log, LogTag

def print_validation_result(constraint, result):
    log(result.summary)

    if result.errors:
        log("errors:")
        for err in result.errors:
            log(f"  - {err}")

    for case in result.test_case_results:
        log(
            f"row={case.row.values}, "
            f"expected_truth={case.expected_truth}, "
            f"actual_truth={case.actual_truth}, "
            f"expected_pass={case.expected_pass}, "
            f"actual_pass={case.actual_pass}, "
            f"reason={case.rationale}"
        )

    for case in result.sql_test_case_results:
        log(
            f"name={case.name}, "
            f"expected_pass={case.expected_pass}, "
            f"actual_pass={case.actual_pass}, "
            f"reason={case.rationale}, "
        )


def run_validation():
    generator = CheckCodeGenerator()
    evaluator = ConstraintSemanticEvaluator()
    test_generator = TestCaseGenerator()
    validator = CheckValidator(evaluator, test_generator)

    constraints = test_generator.generate_constraints()

    for constraint in constraints:
        artifacts = generator.generate(constraint)

        log(f"\n===== {constraint.constraint_name} {constraint.original_check_sql} =====")
        log("\n=== COMBINED SQL ===")
        log(artifacts.combined_sql)

        with db_session() as db_conn:
            if isinstance(constraint.condition, ExistsExpr):
                result = validator.validate_exists_constraint(
                    constraint=constraint,
                    artifacts=artifacts,
                    db_conn=db_conn,
                )
            else:
                result = validator.validate(
                    constraint=constraint,
                    artifacts=artifacts,
                    db_conn=db_conn,
                )

        print_validation_result(constraint, result)


def main():
    try:
        run_validation()
    except Exception as e:
        log(f"[-] Error: {e}")


if __name__ == "__main__":
    main()