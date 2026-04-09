import argparse
import sys
from pathlib import Path

from psycopg import Cursor
from psycopg.rows import TupleRow

from compiler.codegen import CheckCodeGenerator
from compiler.contracts import (
    AndExpr,
    ColumnExpr,
    CompareExpr,
    ExistsExpr,
    LiteralExpr,
    OrExpr,
    StatementType,
    TransformedCheckConstraint,
)
from compiler.benchmark import run_benchmarks
from compiler.validator import CheckValidator
from compiler.evaluator import ConstraintSemanticEvaluator
from compiler.testgenerator import TestCaseGenerator
from compiler.validator import CheckValidator
from lib.client import db_session
from lib.util import (
    clone_schema,
    drop_schema,
    set_to_test_schema,
    validate_sql_file_verbose,
)
from parser_transformer.classifier import classify_and_extract
from parser_transformer.extractor import (
    extract_raw_checks_from_statement,
    extract_table_schema_from_original_sql,
)
from parser_transformer.file_parser import split_sql_statements
from parser_transformer.tokens_parser import CheckExprParser
from parser_transformer.transformer import collect_referenced_columns
from util.log import LogTag, banner, log, log_testcase, underline


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


def validate_sql_file_path(path_str: str) -> Path:
    path = Path(path_str)

    if not path.exists():
        raise argparse.ArgumentTypeError(f"File does not exist: {path}")

    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Path is not a file: {path}")

    if path.suffix.lower() != ".sql":
        raise argparse.ArgumentTypeError(f"Invalid file type (expected .sql): {path}")

    return path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check Constraint Compiler - SQL Input Reader"
    )

    parser.add_argument(
        "file", type=validate_sql_file_path, help="Path to the .sql file"
    )

    return parser.parse_args()


def format_expr(expr, indent=0):
    pad = "  " * indent

    if isinstance(expr, OrExpr):
        return (
            f"OrExpr(\n"
            f"{pad}  left={format_expr(expr.left, indent + 1)},\n"
            f"{pad}  right={format_expr(expr.right, indent + 1)}\n"
            f"{pad})"
        )

    if isinstance(expr, AndExpr):
        return (
            f"AndExpr(\n"
            f"{pad}  left={format_expr(expr.left, indent + 1)},\n"
            f"{pad}  right={format_expr(expr.right, indent + 1)}\n"
            f"{pad})"
        )

    if isinstance(expr, CompareExpr):
        return (
            f"CompareExpr(\n"
            f"{pad}  left={format_expr(expr.left, indent + 1)},\n"
            f"{pad}  operator='{expr.operator}',\n"
            f"{pad}  right={format_expr(expr.right, indent + 1)}\n"
            f"{pad})"
        )

    if isinstance(expr, ColumnExpr):
        return f"ColumnExpr('{expr.original_name}', '{expr.trigger_reference}')"

    if isinstance(expr, LiteralExpr):
        return f"LiteralExpr({expr.value}, {expr.literal_type})"

    return f"{pad}{expr}"


def setup_test_environment(cur: Cursor[TupleRow]) -> None:
    log("Setting up isolated test environment...", LogTag.INFO)
    drop_schema(cursor=cur)
    clone_schema(cursor=cur)
    log("Environment ready.", LogTag.INFO)


def main():
    banner("Program started. Loading SQL file")
    args = parse_args()
    sql_path: Path = args.file

    with db_session() as db_conn:
        try:
            sql_text = sql_path.read_text(encoding="utf-8")
            log("Successfully loaded SQL file", LogTag.INFO)

            setup_test_environment(cur=db_conn)
            validate_sql_file_verbose(cursor=db_conn, file_path=sql_path)

            statements = split_sql_statements(sql_text)

            transformedCheckConstraints = []
            banner("Parser Running")
            for stmt in statements:
                schema = None
                classified_statement = classify_and_extract(stmt)
                raw_checks = extract_raw_checks_from_statement(classified_statement)
                if classified_statement.statement_type == StatementType.CREATE_TABLE:
                    schema = extract_table_schema_from_original_sql(
                        classified_statement.original_sql
                    )

                for raw_check in raw_checks:
                    condition = CheckExprParser.parse_check_expression(
                        raw_check.check_expr_sql
                    )
                    referenced_column_names = collect_referenced_columns(condition)
                    referenced_columns = []
                    for column_name in referenced_column_names:
                        if schema:
                            referenced_columns.append(
                                (column_name, schema.get(column_name))
                            )
                        else:
                            referenced_columns.append((column_name, "UNKNOWN"))

                    transformedCheckConstraints.append(
                        TransformedCheckConstraint(
                            table_name=raw_check.table_name,
                            constraint_name=raw_check.constraint_name,
                            condition=condition,
                            referenced_columns=referenced_columns,
                            original_check_sql=raw_check.original_check_sql,
                        )
                    )

                    log(f"Condition: {condition}", LogTag.INFO)

            log(
                f"Total TransformedCheckConstraint: {len(transformedCheckConstraints)}",
                LogTag.INFO,
            )
            banner("CodeGen and Validation Running")
            # log(transformedCheckConstraints)
            set_to_test_schema(cursor=db_conn)

            generator = CheckCodeGenerator()
            evaluator = ConstraintSemanticEvaluator()
            test_generator = TestCaseGenerator()
            validator = CheckValidator(evaluator, test_generator)

            for i in range(len(transformedCheckConstraints)):
                constraint = transformedCheckConstraints[i]
                artifacts = generator.generate(constraint)

                log_testcase(
                    constraint.constraint_name,
                    constraint.original_check_sql,
                    artifacts.combined_sql,
                )

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

                if i != len(transformedCheckConstraints) - 1:
                    underline()
            
            banner("Performance Testing Running")
            run_benchmarks(
                row_level_row_counts=[1_000, 10_000, 100_000, 1_000_000],
                table_level_row_counts=[100, 200, 500, 1_000],
                reps=3,
                csv_output_path="benchmark_results.csv",
            )

            banner("Program Completed. Exiting.")

        except Exception as e:
            log(f"Failed to run compiler: {e}", LogTag.ERROR)
            sys.exit(1)
        finally:
            # Ensure connection is closed even if sys.exit is called
            if db_conn:
                db_conn.close()
if __name__ == "__main__":
    main()
