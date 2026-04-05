import argparse
import re
import sys
from typing import List, Dict, Optional

from lib.client import db_session, get_connection
from lib.util import clone_schema, drop_schema
from compiler.codegen import CheckCodeGenerator
from compiler.validator import CheckValidator
from compiler.contracts import ExistsExpr, TransformedCheckConstraint
from compiler.evaluator import ConstraintSemanticEvaluator
from compiler.testgenerator import TestCaseGenerator

def run_exists_validation():
    constraint = TransformedCheckConstraint(
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
)

    generator = CheckCodeGenerator()
    evaluator = ConstraintSemanticEvaluator()
    test_generator = TestCaseGenerator()
    validator = CheckValidator(evaluator, test_generator)

    artifacts = generator.generate(constraint)

    with db_session() as db_conn:
        result = validator.validate_exists_constraint(
            constraint=constraint,
            artifacts=artifacts,
            db_conn=db_conn,
        )

    print(result.summary)

    for test_result in result.sql_test_case_results:
        ok = test_result.expected_pass == test_result.actual_pass
        print(
            f"{test_result.name}: "
            f"expected={test_result.expected_pass}, "
            f"actual={test_result.actual_pass}, "
            f"ok={ok}"
        )
        if test_result.execution_message:
            print(f"  message: {test_result.execution_message}")

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
        run_exists_validation()
    except Exception as e:
        print(f"[-] Error: {e}")

    # Run Compiler
    try:
        pass
    except Exception as e:
        print(f"[-] Error: {e}")


if __name__ == "__main__":
    main()
