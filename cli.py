import argparse
import re
import sys
from typing import List, Dict, Optional

from lib.client import db_session, get_connection
from lib.util import clone_schema, drop_schema


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

    # Run Compiler
    try:
        pass
    except Exception as e:
        print(f"[-] Error: {e}")


if __name__ == "__main__":
    main()
