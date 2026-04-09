import time
import csv
import statistics
from dataclasses import dataclass, field
from typing import Optional

from util.log import log, LogTag, banner
from lib.client import get_connection
from compiler.codegen import CheckCodeGenerator
from compiler.contracts import (
    TransformedCheckConstraint,
    ExistsExpr,
    OrExpr,
    AndExpr,
    CompareExpr,
    ColumnExpr,
    LiteralExpr,
    LiteralType,
)

from conf.config import TEST_SCHEMA


@dataclass
class BenchmarkResult:
    constraint_name: str
    enforcement_mode: str       # "native_check" | "trigger" | "no_constraint"
    row_count: int
    operation: str
    mean_seconds: float
    stddev_seconds: float
    reps: int
    rows_affected: int
    ops_per_second: float       # based on mean


@dataclass
class BenchmarkSuite:
    results: list[BenchmarkResult] = field(default_factory=list)

    def add(self, result: BenchmarkResult):
        self.results.append(result)

    def to_csv(self, filepath: str):
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "constraint_name",
                "enforcement_mode",
                "row_count",
                "operation",
                "mean_seconds",
                "stddev_seconds",
                "reps",
                "rows_affected",
                "ops_per_second",
            ])
            for r in self.results:
                writer.writerow([
                    r.constraint_name,
                    r.enforcement_mode,
                    r.row_count,
                    r.operation,
                    f"{r.mean_seconds:.6f}",
                    f"{r.stddev_seconds:.6f}",
                    r.reps,
                    r.rows_affected,
                    f"{r.ops_per_second:.2f}",
                ])

    def print_summary(self):
        log("Performance Benchmark Results", LogTag.INFO)
        header = (
            f"{'Constraint':<30} {'Mode':<16} {'Rows':<8} "
            f"{'Operation':<25} {'Mean(s)':<12} {'StdDev':<12} {'Reps':<5} {'Ops/s':<12}"
        )
        log(header, LogTag.INFO)
        log("-" * len(header), LogTag.INFO)
        for r in self.results:
            log(
                f"{r.constraint_name:<30} {r.enforcement_mode:<16} {r.row_count:<8} "
                f"{r.operation:<25} {r.mean_seconds:<12.6f} {r.stddev_seconds:<12.6f} "
                f"{r.reps:<5} {r.ops_per_second:<12.2f}",
                LogTag.INFO,
            )


ROW_LEVEL_TABLE = "bench_products"
TABLE_LEVEL_TABLE = "bench_employees"

ROW_LEVEL_ROW_COUNTS = [1_000, 10_000, 100_000, 1_000_000]

# table-level EXISTS triggers use O(n^2) self-join so large counts are impractical
TABLE_LEVEL_ROW_COUNTS = [100, 200, 500, 1_000]

DEFAULT_REPS = 3

# row-level: CHECK ((price > 100 AND discounted_price > 0) OR (price <= 100))
ROW_LEVEL_CONSTRAINT = TransformedCheckConstraint(
    table_name=ROW_LEVEL_TABLE,
    constraint_name="bench_chk_price",
    condition=OrExpr(
        left=AndExpr(
            left=CompareExpr(
                left=ColumnExpr("price", "NEW.price"),
                operator=">",
                right=LiteralExpr(100, LiteralType.NUMBER),
            ),
            right=CompareExpr(
                left=ColumnExpr("discounted_price", "NEW.discounted_price"),
                operator=">",
                right=LiteralExpr(0, LiteralType.NUMBER),
            ),
        ),
        right=CompareExpr(
            left=ColumnExpr("price", "NEW.price"),
            operator="<=",
            right=LiteralExpr(100, LiteralType.NUMBER),
        ),
    ),
    referenced_columns=[("price", "NUMERIC"), ("discounted_price", "NUMERIC")],
    original_check_sql="CHECK ((price > 100 AND discounted_price > 0) OR (price <= 100))",
)

# table-level: CHECK NOT EXISTS (FD self-join)
TABLE_LEVEL_CONSTRAINT = TransformedCheckConstraint(
    table_name=TABLE_LEVEL_TABLE,
    constraint_name="bench_fd_position_salary",
    condition=ExistsExpr(
        query_sql=f"""
SELECT *
FROM {TABLE_LEVEL_TABLE} e1, {TABLE_LEVEL_TABLE} e2
WHERE e1.position = e2.position
AND e1.salary <> e2.salary
""",
        negated=True,
    ),
    referenced_columns=[],
    original_check_sql=f"""CHECK NOT EXISTS (
SELECT *
FROM {TABLE_LEVEL_TABLE} e1, {TABLE_LEVEL_TABLE} e2
WHERE e1.position = e2.position
AND e1.salary <> e2.salary
)""",
)


def _set_schema(conn):
    """Isolate benchmark work in the test schema."""
    cur = conn.cursor()
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA};")
    cur.execute(f"SET search_path TO {TEST_SCHEMA}, public;")
    conn.commit()
    cur.close()


def _create_row_level_table_sql(table_name: str) -> str:
    return f"""
DROP TABLE IF EXISTS {table_name} CASCADE;
CREATE TABLE {table_name} (
    id BIGSERIAL PRIMARY KEY,
    price NUMERIC,
    discounted_price NUMERIC,
    description TEXT
);
""".strip()


def _create_table_level_table_sql(table_name: str) -> str:
    return f"""
DROP TABLE IF EXISTS {table_name} CASCADE;
CREATE TABLE {table_name} (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    position TEXT NOT NULL,
    salary NUMERIC NOT NULL,
    notes TEXT
);
""".strip()


def _add_native_check_row_level(table_name: str) -> str:
    return f"""
ALTER TABLE {table_name}
ADD CONSTRAINT native_chk_price
CHECK ((price > 100 AND discounted_price > 0) OR (price <= 100));
""".strip()


def _time_execute(conn, sql: str) -> float:
    cur = conn.cursor()
    start = time.perf_counter()
    cur.execute(sql)
    conn.commit()
    elapsed = time.perf_counter() - start
    cur.close()
    return elapsed


def _make_result(cname, mode, n, operation, timings, rows) -> BenchmarkResult:
    mean = statistics.mean(timings)
    stddev = statistics.stdev(timings) if len(timings) > 1 else 0.0
    return BenchmarkResult(
        constraint_name=cname,
        enforcement_mode=mode,
        row_count=n,
        operation=operation,
        mean_seconds=mean,
        stddev_seconds=stddev,
        reps=len(timings),
        rows_affected=rows,
        ops_per_second=rows / mean if mean > 0 else 0,
    )


# workloads for row-level benchmark (products table)

def _insert_constrained_row(table, n):
    """Inserts populating constrained columns (price, discounted_price)."""
    return f"""
INSERT INTO {table} (price, discounted_price, description)
SELECT (10 + (g % 80))::NUMERIC, (1 + (g % 50))::NUMERIC, 'item_' || g
FROM generate_series(1, {n}) AS g;
""".strip()


def _insert_unconstrained_row(table, n):
    """Inserts only the unconstrained column. Constrained cols left NULL
    so CHECK evaluates to UNKNOWN which passes under 3VL."""
    return f"""
INSERT INTO {table} (description)
SELECT 'item_' || g
FROM generate_series(1, {n}) AS g;
""".strip()


def _update_constrained_row(table):
    return f"UPDATE {table} SET price = (10 + (id % 80))::NUMERIC;"


def _update_unconstrained_row(table):
    return f"UPDATE {table} SET description = 'updated_' || id;"


def _read_constrained_row(table):
    return f"SELECT * FROM {table} WHERE price > 50;"


def _read_unconstrained_row(table):
    return f"SELECT * FROM {table} WHERE description LIKE 'item_1%';"


# workloads for table-level benchmark (employees table)

def _insert_constrained_tbl(table, n):
    return f"""
INSERT INTO {table} (name, position, salary, notes)
SELECT 'emp_' || g, 'position_' || g, (3000 + (g % 5000))::NUMERIC, 'notes_' || g
FROM generate_series(1, {n}) AS g;
""".strip()


def _insert_unconstrained_tbl(table, n):
    """Unconstrained insert — still supplies NOT NULL cols but salary
    is fixed so it doesn't really exercise the FD constraint path."""
    return f"""
INSERT INTO {table} (name, position, salary, notes)
SELECT 'emp_' || g, 'pos_' || g, 5000, 'note_' || g
FROM generate_series(1, {n}) AS g;
""".strip()


def _update_constrained_tbl(table):
    return f"UPDATE {table} SET salary = salary;"


def _update_unconstrained_tbl(table):
    return f"UPDATE {table} SET notes = 'updated_' || id;"


def _read_constrained_tbl(table):
    return f"SELECT * FROM {table} WHERE salary > 5000;"


def _read_unconstrained_tbl(table):
    return f"SELECT * FROM {table} WHERE notes LIKE 'notes_1%';"


def _setup_row_table(cur, conn, table, mode, artifacts):
    cur.execute(_create_row_level_table_sql(table))
    conn.commit()
    if mode == "native_check":
        cur.execute(_add_native_check_row_level(table))
        conn.commit()
    elif mode == "trigger":
        cur.execute(artifacts.combined_sql)
        conn.commit()


def _setup_tbl_table(cur, conn, table, mode, artifacts):
    cur.execute(_create_table_level_table_sql(table))
    conn.commit()
    if mode == "trigger":
        cur.execute(artifacts.combined_sql)
        conn.commit()


def _run_row_level_benchmark(conn, suite, row_counts, reps):
    """
    6 operations x 3 modes x N row counts x R reps.
    Operations: insert/update/read on constrained and unconstrained columns.
    """
    codegen = CheckCodeGenerator()
    constraint = ROW_LEVEL_CONSTRAINT
    artifacts = codegen.generate(constraint)
    table = ROW_LEVEL_TABLE
    name = constraint.constraint_name

    for mode in ["no_constraint", "native_check", "trigger"]:
        for n in row_counts:
            log(f"Row-level | mode={mode} | rows={n} | reps={reps}", LogTag.INFO)
            cur = conn.cursor()

            # 1. insert_constrained — fresh table each rep
            timings = []
            for _ in range(reps):
                _setup_row_table(cur, conn, table, mode, artifacts)
                timings.append(_time_execute(conn, _insert_constrained_row(table, n)))
            suite.add(_make_result(name, mode, n, "insert_constrained", timings, n))

            # 2. insert_unconstrained — fresh table each rep
            timings = []
            for _ in range(reps):
                _setup_row_table(cur, conn, table, mode, artifacts)
                timings.append(_time_execute(conn, _insert_unconstrained_row(table, n)))
            suite.add(_make_result(name, mode, n, "insert_unconstrained", timings, n))

            # seed table once for update and read benchmarks
            _setup_row_table(cur, conn, table, mode, artifacts)
            cur.execute(_insert_constrained_row(table, n))
            conn.commit()

            # 3. update_constrained
            timings = [_time_execute(conn, _update_constrained_row(table)) for _ in range(reps)]
            suite.add(_make_result(name, mode, n, "update_constrained", timings, n))

            # 4. update_unconstrained
            timings = [_time_execute(conn, _update_unconstrained_row(table)) for _ in range(reps)]
            suite.add(_make_result(name, mode, n, "update_unconstrained", timings, n))

            # 5. read_constrained
            timings = [_time_execute(conn, _read_constrained_row(table)) for _ in range(reps)]
            suite.add(_make_result(name, mode, n, "read_constrained", timings, n))

            # 6. read_unconstrained
            timings = [_time_execute(conn, _read_unconstrained_row(table)) for _ in range(reps)]
            suite.add(_make_result(name, mode, n, "read_unconstrained", timings, n))

            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            conn.commit()
            cur.close()


def _run_table_level_benchmark(conn, suite, row_counts, reps):
    """
    6 operations x 2 modes x N row counts x R reps.
    No native_check mode since postgres doesn't support subqueries in CHECK.
    """
    codegen = CheckCodeGenerator()
    constraint = TABLE_LEVEL_CONSTRAINT
    artifacts = codegen.generate(constraint)
    table = TABLE_LEVEL_TABLE
    name = constraint.constraint_name

    for mode in ["no_constraint", "trigger"]:
        for n in row_counts:
            log(f"Table-level | mode={mode} | rows={n} | reps={reps}", LogTag.INFO)
            cur = conn.cursor()

            # 1. insert_constrained
            timings = []
            for _ in range(reps):
                _setup_tbl_table(cur, conn, table, mode, artifacts)
                timings.append(_time_execute(conn, _insert_constrained_tbl(table, n)))
            suite.add(_make_result(name, mode, n, "insert_constrained", timings, n))

            # 2. insert_unconstrained
            timings = []
            for _ in range(reps):
                _setup_tbl_table(cur, conn, table, mode, artifacts)
                timings.append(_time_execute(conn, _insert_unconstrained_tbl(table, n)))
            suite.add(_make_result(name, mode, n, "insert_unconstrained", timings, n))

            # seed for update and read
            _setup_tbl_table(cur, conn, table, mode, artifacts)
            cur.execute(_insert_constrained_tbl(table, n))
            conn.commit()

            # 3. update_constrained
            timings = [_time_execute(conn, _update_constrained_tbl(table)) for _ in range(reps)]
            suite.add(_make_result(name, mode, n, "update_constrained", timings, n))

            # 4. update_unconstrained
            timings = [_time_execute(conn, _update_unconstrained_tbl(table)) for _ in range(reps)]
            suite.add(_make_result(name, mode, n, "update_unconstrained", timings, n))

            # 5. read_constrained
            timings = [_time_execute(conn, _read_constrained_tbl(table)) for _ in range(reps)]
            suite.add(_make_result(name, mode, n, "read_constrained", timings, n))

            # 6. read_unconstrained
            timings = [_time_execute(conn, _read_unconstrained_tbl(table)) for _ in range(reps)]
            suite.add(_make_result(name, mode, n, "read_unconstrained", timings, n))

            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            conn.commit()
            cur.close()


def run_benchmarks(
    row_level_row_counts: Optional[list[int]] = None,
    table_level_row_counts: Optional[list[int]] = None,
    reps: int = DEFAULT_REPS,
    csv_output_path: Optional[str] = None,
) -> BenchmarkSuite:
    if row_level_row_counts is None:
        row_level_row_counts = ROW_LEVEL_ROW_COUNTS
    if table_level_row_counts is None:
        table_level_row_counts = TABLE_LEVEL_ROW_COUNTS

    suite = BenchmarkSuite()
    conn = get_connection()
    conn.autocommit = False

    try:
        # run everything in the test schema
        _set_schema(conn)

        banner("Row-Level Constraint Benchmark (chk_price)")
        _run_row_level_benchmark(conn, suite, row_level_row_counts, reps)

        banner("Table-Level Constraint Benchmark (fd_position_salary)")
        _run_table_level_benchmark(conn, suite, table_level_row_counts, reps)

    except Exception as e:
        log(f"Benchmark failed: {e}", LogTag.ERROR)
        raise
    finally:
        try:
            cur = conn.cursor()
            cur.execute(f"DROP TABLE IF EXISTS {ROW_LEVEL_TABLE} CASCADE;")
            cur.execute(f"DROP TABLE IF EXISTS {TABLE_LEVEL_TABLE} CASCADE;")
            conn.commit()
            cur.close()
        except Exception:
            pass
        conn.close()

    suite.print_summary()

    if csv_output_path:
        suite.to_csv(csv_output_path)
        log(f"Results written to {csv_output_path}", LogTag.INFO)

    return suite
