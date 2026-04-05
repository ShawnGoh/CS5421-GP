import argparse
import sys

from lib.client import db_session, get_connection
from lib.executor import validate_sql
from lib.util import clone_schema, drop_schema


def setup_test_environment() -> None:
    print("[*] Setting up isolated test environment...")
    with db_session() as cur:
        drop_schema(cursor=cur)
        clone_schema(cursor=cur)
    print("[+] Environment ready.")


def validate_input_sql(raw_sql: str) -> None:
    print(f"[*] Validating input SQL...")
    with db_session() as cur:
        if not validate_sql(cursor=cur, raw_sql=raw_sql):
            raise ValueError("The provided SQL statement is invalid.")
    print("[+] Input SQL passed validation.")


def main():
    parser = argparse.ArgumentParser(description="Auto-Column Discovery SQL Compiler")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", type=str, help="Full CREATE TABLE statement")
    group.add_argument("--alter", type=str, help="Full ALTER TABLE statement")

    args = parser.parse_args()
    input_sql = args.create or args.alter

    db_conn = get_connection()
    try:
        # 1. Environment Preparation
        setup_test_environment()

        # 2. Initial Validation (Dry-Run)
        validate_input_sql(input_sql)

        # 3. Compiler Pipeline (Placeholders for your next steps)
        # parsed_ast = parse_sql(input_sql)
        # generated_sql = generate_compiler_logic(parsed_ast)

        # 4. Final Validation of Generated Logic
        # validate_sql(cursor=cur, raw_sql=generated_sql)

        print("[+] Compilation and validation successful.")

    except Exception as e:
        print(f"[-] Compiler Error: {e}")
        sys.exit(1)

    finally:
        # Ensure connection is closed even if sys.exit is called
        if db_conn:
            db_conn.close()


if __name__ == "__main__":
    main()
