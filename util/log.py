from datetime import datetime
from enum import Enum
from functools import cache
from textwrap import indent
import os
from types import TracebackType

from conf.config import DEFAULT_LOG_DIR


class LogTag(str, Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"
    WARNING = "WARNING"
    ERROR = "ERROR"


# Fixed widths
TAG_WIDTH = 7
TOTAL_WIDTH = 250
SQL_INDENT = " " * 32


class Logger:
    __slots__ = ("_file", "log_path")

    def __init__(self, log_dir: str | None = None):
        """
        Initialise the logger.

        Args:
            log_dir: Directory to write log files into. Each execution creates
                     a new file named by the current timestamp, e.g.
                     ``run_11Apr_1023.log``.
                     Defaults to ``/log`` sitting alongside ``/util``.
        """
        self._file = None
        self.log_path: str | None = None
        resolved_dir = os.path.realpath(log_dir or DEFAULT_LOG_DIR)
        os.makedirs(resolved_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%d%b_%H%M")
        self.log_path = os.path.join(resolved_dir, f"run_{timestamp}.log")
        self._file = open(self.log_path, "w", encoding="utf-8")

    def _write(self, line: str) -> None:
        """Write *line* to stdout and, if configured, to the log file."""
        print(line)
        if self._file:
            self._file.write(line + "\n")
            self._file.flush()

    def log(self, message: str, tag: LogTag = LogTag.INFO) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tag_str = f"{tag.value:<{TAG_WIDTH}}"
        self._write(f"{timestamp} [{tag_str}] | {message}")

    def banner(self, msg: str) -> None:
        padding = "=" * TOTAL_WIDTH
        self._write(padding)
        self.log(f"{msg} ")
        self._write(padding)

    def log_testcase(
        self,
        constraint_name: str,
        original_check_sql: str,
        body: str | None = None,
    ) -> None:
        self.log(
            f"Constraint Name: {constraint_name} | "
            f"Original Check Constraint: {original_check_sql}"
        )
        if body:
            indented = indent(body, SQL_INDENT)
            self._write(indented)

    def underline(self) -> None:
        self._write("=" * TOTAL_WIDTH)

    def close(self) -> None:
        """Flush and close the log file (no-op if no file was configured)."""
        if self._file:
            self._file.flush()
            self._file.close()
            self._file = None

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()


@cache
def get_logger(log_dir: str | None = None) -> Logger:
    return Logger(log_dir)


# API functions for backwards compatibility.
def log(message: str, tag: LogTag = LogTag.INFO) -> None:
    get_logger().log(message, tag)


def banner(msg: str) -> None:
    get_logger().banner(msg)


def log_testcase(
    constraint_name: str, original_check_sql: str, body: str | None = None
) -> None:
    get_logger().log_testcase(constraint_name, original_check_sql, body)


def underline() -> None:
    get_logger().underline()
