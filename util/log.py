from datetime import datetime
from enum import Enum
from textwrap import indent


class LogTag(str, Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"
    WARNING = "WARNING"
    ERROR = "ERROR"


# Fixed widths
TAG_WIDTH = 7
TOTAL_WIDTH = 250
SQL_INDENT = " " * 32

def log(message: str, tag: LogTag = LogTag.INFO) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Pad tag to fixed width (left-aligned)
    tag_str = f"{tag.value:<{TAG_WIDTH}}"

    print(f"{timestamp} [{tag_str}] | {message}")

def banner(msg: str):
    padding = "=" * TOTAL_WIDTH
    print(f"{padding}")
    log(f"{msg} ")
    print(f"{padding}")
    


def log_testcase(constraint_name: str, original_check_sql: str, body: str | None = None):
    log(f"Constraint Name: {constraint_name} | Original Check Constraint: {original_check_sql}")
    if body:
        print(indent(body, SQL_INDENT))

def underline():
    padding = "=" * TOTAL_WIDTH
    print(f"{padding}")