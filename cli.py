import argparse
import re
import sys
from typing import List, Dict, Optional

from lib.client import db_session, get_connection
from lib.util import clone_schema, drop_schema
from compiler.codegen import CheckCodeGenerator
from compiler.validator import CheckValidator
from compiler.contracts import ExistsExpr, TransformedCheckConstraint, ValidationRequest
from compiler.evaluator import ConstraintSemanticEvaluator
from compiler.testgenerator import TestCaseGenerator

def print_validation_result(constraint, result):
    print(f"\n===== {constraint.constraint_name} {constraint.original_check_sql} =====")
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
    parser = argparse.ArgumentParser(description="Auto-Column Discovery SQL Compiler")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", type=str, help="Full CREATE TABLE statement")
    group.add_argument("--alter", type=str, help="Full ALTER TABLE statement")

    args = parser.parse_args()

    # Db connection to clone environment
    db_conn = get_connection()
    try:
        with db_session() as cur:
            drop_schema(cursor=cur)
            clone_schema(cursor=cur)
    finally:
        db_conn.close()


    try:
        run_validation()
    except Exception as e:
        print(f"[-] Error: {e}")

    # Run Compiler
    try:
        pass
    except Exception as e:
        print(f"[-] Error: {e}")


if __name__ == "__main__":
    main()
