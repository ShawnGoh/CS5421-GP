import argparse
import sys
from pathlib import Path
from util.log import log, LogTag
from compiler.contracts import StatementType, TableRef, ClassifiedStatement
from parser_transformer.classifier import classify_and_extract
from parser_transformer.file_parser import split_sql_statements
from parser_transformer.extractor import extract_raw_checks_from_statement, extract_table_schema_from_original_sql
from parser_transformer.transformer import tokenize, reject_unsupported_features


def validate_sql_file(path_str: str) -> Path:
    path = Path(path_str)

    if not path.exists():
        raise argparse.ArgumentTypeError(f"File does not exist: {path}")

    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Path is not a file: {path}")

    if path.suffix.lower() != ".sql":
        raise argparse.ArgumentTypeError(
            f"Invalid file type (expected .sql): {path}"
        )
        
    return path

def parse_args():
    parser = argparse.ArgumentParser(
        description="Check Constraint Compiler - SQL Input Reader"
    )

    parser.add_argument(
        "file",
        type=validate_sql_file,
        help="Path to the .sql file"
    )

    return parser.parse_args()

def main():
    args = parse_args()
    sql_path: Path = args.file

    try:
        sql_text = sql_path.read_text(encoding="utf-8")
        log("Successfully loaded SQL file", LogTag.INFO)
    except Exception as e:
        log(f"Failed to read file: {e}", LogTag.ERROR)
        sys.exit(1)
    
    statements = split_sql_statements(sql_text)
    
    for stmt in statements:
        classified_statement = classify_and_extract(stmt)
        raw_checks = extract_raw_checks_from_statement(classified_statement)
        if classified_statement.statement_type == StatementType.CREATE_TABLE:
            schema = extract_table_schema_from_original_sql(classified_statement.original_sql)
        
        for raw_check in raw_checks:
            try:
                reject_unsupported_features(raw_check.check_expr_sql)
                raw_check.tokens = tokenize(raw_check.check_expr_sql)
            except Exception as e:
                log(f"Unsupported Feature detected in Check expression: {e}", LogTag.ERROR)
                break


if __name__ == "__main__":
    main()