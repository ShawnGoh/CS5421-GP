import argparse
import sys

from lib.client import db_session, get_connection
from lib.executor import validate_sql
from lib.util import clone_schema, drop_schema
from compiler.codegen import CheckCodeGenerator
from compiler.validator import CheckValidator
from compiler.contracts import ExistsExpr, TransformedCheckConstraint, ValidationRequest
from compiler.evaluator import ConstraintSemanticEvaluator
from compiler.testgenerator import TestCaseGenerator

def print_validation_result(constraint, result):
    print(result.summary)

    for case in result.test_case_results:
        print(
            f"row={case.row.values}, "
            f"expected_truth={case.expected_truth}, "
            f"actual_truth={case.actual_truth}, "
            f"expected_pass={case.expected_pass}, "
            f"actual_pass={case.actual_pass}, "
            f"reason={case.rationale}"
        )

    for case in result.sql_test_case_results:
        print(
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
        print(f"\n===== {constraint.constraint_name} {constraint.original_check_sql} =====")
        print("\n=== COMBINED SQL ===")
        print(artifacts.combined_sql)

        if isinstance(constraint.condition, ExistsExpr):
            with db_session() as db_conn:
                result = validator.validate_exists_constraint(
                    constraint=constraint,
                    artifacts=artifacts,
                    db_conn=db_conn,
                )
        else:
            request = ValidationRequest(
                constraint=constraint,
                artifacts=artifacts,
            )
            result = validator.validate(request)

        print_validation_result(constraint, result)


def main():
    try:
        run_validation()
    except Exception as e:
        print(f"[-] Error: {e}")


if __name__ == "__main__":
    main()
