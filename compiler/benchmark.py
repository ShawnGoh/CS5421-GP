from datetime import datetime
import time
import csv
import statistics
from dataclasses import dataclass, field
from typing import Optional

from util.log import log, LogTag, banner
from lib.client import get_connection
from compiler.contracts import ExistsExpr, OutputCheck, TransformedCheckConstraint

from conf.config import TEST_SCHEMA


@dataclass
class BenchmarkResult:
    table_name: str
    enforcement_mode: str       # "native_check" | "trigger" | "no_constraint"
    row_count: int
    operation: str
    mean_seconds: float
    stddev_seconds: float
    reps: int
    rows_affected: int
    ops_per_second: float
    note: str = ""              # e.g. "seed_failed", "NA", etc.


@dataclass
class BenchmarkSuite:
    results: list[BenchmarkResult] = field(default_factory=list)

    def add(self, result: BenchmarkResult):
        self.results.append(result)

    def to_csv(self, filepath: str):
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "table_name",
                "enforcement_mode",
                "row_count",
                "operation",
                "mean_seconds",
                "stddev_seconds",
                "reps",
                "rows_affected",
                "ops_per_second",
                "note",
            ])
            for r in self.results:
                writer.writerow([
                    r.table_name,
                    r.enforcement_mode,
                    r.row_count,
                    r.operation,
                    f"{r.mean_seconds:.6f}",
                    f"{r.stddev_seconds:.6f}",
                    r.reps,
                    r.rows_affected,
                    f"{r.ops_per_second:.2f}",
                    r.note,
                ])

    def print_summary(self):
        log("Performance Benchmark Results", LogTag.INFO)
        header = (
            f"{'Table':<20} {'Mode':<16} {'Rows':<8} "
            f"{'Operation':<25} {'Mean(s)':<12} {'StdDev':<12} {'Reps':<5} {'Ops/s':<12} {'Note'}"
        )
        log(header, LogTag.INFO)
        log("-" * 130, LogTag.INFO)
        for r in self.results:
            log(
                f"{r.table_name:<20} {r.enforcement_mode:<16} {r.row_count:<8} "
                f"{r.operation:<25} {r.mean_seconds:<12.6f} {r.stddev_seconds:<12.6f} "
                f"{r.reps:<5} {r.ops_per_second:<12.2f} {r.note}",
                LogTag.INFO,
            )


# type -> generate_series expression for that type
TYPE_GENERATORS = {
    "NUMERIC":  "(10 + (g % 80))::NUMERIC",
    "DECIMAL":  "(10 + (g % 80))::NUMERIC",
    "INT":      "g",
    "INTEGER":  "g",
    "BIGINT":   "g::BIGINT",
    "SMALLINT": "(g % 30000)::SMALLINT",
    "REAL":     "(g * 1.5)::REAL",
    "FLOAT":    "(g * 1.5)::FLOAT",
    "TEXT":     "'val_' || g",
    "VARCHAR":  "'val_' || g",
    "CHAR":     "'v'",
    "BOOLEAN":  "TRUE",
    "BOOL":     "TRUE",
}

DEFAULT_ROW_COUNTS = [1_000, 10_000, 100_000, 1_000_000]
EXISTS_ROW_COUNTS = [100, 200, 500, 1_000]
DEFAULT_REPS = 3


def _set_schema(conn):
    cur = conn.cursor()
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA};")
    cur.execute(f"SET search_path TO {TEST_SCHEMA}, public;")
    conn.commit()
    cur.close()


def _time_execute(conn, sql: str) -> float:
    cur = conn.cursor()
    start = time.perf_counter()
    cur.execute(sql)
    conn.commit()
    elapsed = time.perf_counter() - start
    cur.close()
    return elapsed


def _reset_conn(conn):
    """Ensure connection is in a clean transaction state."""
    try: conn.rollback()
    except: pass


def _make_result(table, mode, n, op, timings, rows, note="") -> BenchmarkResult:
    mean = statistics.mean(timings)
    stddev = statistics.stdev(timings) if len(timings) > 1 else 0.0
    return BenchmarkResult(
        table_name=table,
        enforcement_mode=mode,
        row_count=n,
        operation=op,
        mean_seconds=mean,
        stddev_seconds=stddev,
        reps=len(timings),
        rows_affected=rows,
        ops_per_second=rows / mean if mean > 0 else 0,
        note=note,
    )


def _na_result(table, mode, n, op, rows, note="NA") -> BenchmarkResult:
    return BenchmarkResult(
        table_name=table,
        enforcement_mode=mode,
        row_count=n,
        operation=op,
        mean_seconds=0,
        stddev_seconds=0,
        reps=0,
        rows_affected=rows,
        ops_per_second=0,
        note=note,
    )


# build a bare CREATE TABLE from schema dict (no constraints)
def _bare_table_sql(table_name: str, schema: dict) -> str:
    cols = ",\n    ".join(f"{name} {typ}" for name, typ in schema.items())
    return f"DROP TABLE IF EXISTS {table_name} CASCADE;\nCREATE TABLE {table_name} (\n    bench_id BIGSERIAL PRIMARY KEY,\n    {cols}\n);"


# build INSERT SQL using generate_series with type-safe values
def _insert_sql(table_name: str, schema: dict, n: int) -> str:
    cols = []
    exprs = []
    for name, typ in schema.items():
        cols.append(name)
        exprs.append(TYPE_GENERATORS.get(typ.upper(), "'val_' || g") + f" AS {name}")
    return (
        f"INSERT INTO {table_name} ({', '.join(cols)})\n"
        f"SELECT {', '.join(exprs)}\n"
        f"FROM generate_series(1, {n}) AS g;"
    )


# build INSERT with NULLs only for constrained columns, typed values for the rest
def _insert_unconstrained_sql(table_name: str, schema: dict, constrained_set: set, n: int) -> str:
    cols = []
    exprs = []
    for name, typ in schema.items():
        cols.append(name)
        if name in constrained_set:
            exprs.append(f"NULL AS {name}")
        else:
            exprs.append(TYPE_GENERATORS.get(typ.upper(), "'val_' || g") + f" AS {name}")
    return (
        f"INSERT INTO {table_name} ({', '.join(cols)})\n"
        f"SELECT {', '.join(exprs)}\n"
        f"FROM generate_series(1, {n}) AS g;"
    )


# split columns into constrained and unconstrained
def _split_columns(schema: dict, constraints: list) -> tuple[list[str], list[str]]:
    constrained_set = set()
    for c, _ in constraints:
        for col_name, _ in c.referenced_columns:
            constrained_set.add(col_name)

    constrained = [name for name in schema if name in constrained_set]
    unconstrained = [name for name in schema if name not in constrained_set]
    return constrained, unconstrained


# generate UPDATE SQL for a specific column
def _update_col_sql(table_name: str, col_name: str, col_type: str) -> str:
    gen = TYPE_GENERATORS.get(col_type.upper(), "'updated_' || bench_id")
    # for updates, replace g with bench_id
    gen = gen.replace("g", "bench_id")
    return f"UPDATE {table_name} SET {col_name} = {gen};"


# generate SELECT SQL filtering on a specific column
def _read_col_sql(table_name: str, col_name: str, col_type: str) -> str:
    upper = col_type.upper()
    if upper in ("NUMERIC", "DECIMAL", "INT", "INTEGER", "BIGINT", "SMALLINT", "REAL", "FLOAT"):
        return f"SELECT * FROM {table_name} WHERE {col_name} > 50;"
    elif upper in ("BOOLEAN", "BOOL"):
        return f"SELECT * FROM {table_name} WHERE {col_name} IS TRUE;"
    else:
        return f"SELECT * FROM {table_name} WHERE {col_name} LIKE 'val_1%';"


def _try_seed(conn, table_name, schema, constrained_set, n):
    """Try inserting typed data. If that fails, try with constrained cols as NULL."""
    try:
        _time_execute(conn, _insert_sql(table_name, schema, n))
        return True
    except Exception:
        try: conn.rollback()
        except: pass

    try:
        _time_execute(conn, _insert_unconstrained_sql(table_name, schema, constrained_set, n))
        return True
    except Exception:
        try: conn.rollback()
        except: pass

    return False


def _setup_table(conn, table_name, schema):
    cur = conn.cursor()
    cur.execute(_bare_table_sql(table_name, schema))
    conn.commit()
    cur.close()


def _install_triggers(conn, artifacts_list):
    cur = conn.cursor()
    for artifacts in artifacts_list:
        cur.execute(artifacts.combined_sql)
    conn.commit()
    cur.close()


def _install_native_checks(conn, table_name, constraints):
    """Try adding each native CHECK. Skip any that fail (EXISTS, etc). Returns count of applied."""
    applied = 0
    for c, _ in constraints:
        try:
            cur = conn.cursor()
            sql = f"ALTER TABLE {table_name} ADD CONSTRAINT bench_{c.constraint_name} {c.original_check_sql};"
            cur.execute(sql)
            conn.commit()
            cur.close()
            applied += 1
        except Exception:
            # rollback and skip this constraint (e.g. EXISTS not supported)
            try:
                conn.rollback()
            except Exception:
                pass
            log(f"  native CHECK skipped (unsupported): {c.constraint_name}", LogTag.WARNING)
    return applied


OPS = [
    "insert_constrained",
    "insert_unconstrained",
    "update_constrained",
    "update_unconstrained",
    "read_constrained",
    "read_unconstrained",
]


def _benchmark_table_mode(
    conn, suite, table_name, schema, mode, constraints, artifacts_list,
    constrained_cols, unconstrained_cols, n, reps
):
    """Run 6 operations for one (table, mode, row_count) combo."""

    c_col = constrained_cols[0] if constrained_cols else None
    c_type = schema.get(c_col, "TEXT") if c_col else "TEXT"
    u_col = unconstrained_cols[0] if unconstrained_cols else "bench_id"
    u_type = schema.get(u_col, "BIGINT") if u_col != "bench_id" else "BIGINT"
    constrained_set = set(constrained_cols)

    def _apply_mode():
        """Install constraints. Returns False if native_check had 0 applied."""
        if mode == "trigger":
            _install_triggers(conn, artifacts_list)
            return True
        elif mode == "native_check":
            applied = _install_native_checks(conn, table_name, constraints)
            return applied > 0
        return True

    # for native_check, check if any constraints are actually applicable
    if mode == "native_check":
        _reset_conn(conn)
        _setup_table(conn, table_name, schema)
        applied = _install_native_checks(conn, table_name, constraints)
        if applied == 0:
            for op in OPS:
                suite.add(_na_result(table_name, mode, n, op, n, "native_check_unsupported"))
            return

    # 1. insert_constrained — fresh table each rep
    timings = []
    for _ in range(reps):
        _reset_conn(conn)
        _setup_table(conn, table_name, schema)
        _apply_mode()
        try:
            t = _time_execute(conn, _insert_sql(table_name, schema, n))
            timings.append(t)
        except Exception:
            _reset_conn(conn)
            break

    if timings:
        suite.add(_make_result(table_name, mode, n, "insert_constrained", timings, n))
    else:
        suite.add(_na_result(table_name, mode, n, "insert_constrained", n, "constraint_violation"))

    # 2. insert_unconstrained
    if unconstrained_cols:
        timings = []
        for _ in range(reps):
            _reset_conn(conn)
            _setup_table(conn, table_name, schema)
            _apply_mode()
            try:
                t = _time_execute(conn, _insert_unconstrained_sql(table_name, schema, constrained_set, n))
                timings.append(t)
            except Exception:
                _reset_conn(conn)
                break

        if timings:
            suite.add(_make_result(table_name, mode, n, "insert_unconstrained", timings, n))
        else:
            suite.add(_na_result(table_name, mode, n, "insert_unconstrained", n, "constraint_violation"))
    else:
        suite.add(_na_result(table_name, mode, n, "insert_unconstrained", n, "no_unconstrained_cols"))

    # seed table for update/read benchmarks
    _reset_conn(conn)
    _setup_table(conn, table_name, schema)
    _apply_mode()

    if not _try_seed(conn, table_name, schema, constrained_set, n):
        for op in ["update_constrained", "update_unconstrained", "read_constrained", "read_unconstrained"]:
            suite.add(_na_result(table_name, mode, n, op, n, "seed_failed"))
        return

    # 3. update_constrained
    if c_col:
        try:
            timings = [_time_execute(conn, _update_col_sql(table_name, c_col, c_type)) for _ in range(reps)]
            suite.add(_make_result(table_name, mode, n, "update_constrained", timings, n))
        except Exception:
            _reset_conn(conn)
            suite.add(_na_result(table_name, mode, n, "update_constrained", n, "constraint_violation"))
    else:
        suite.add(_na_result(table_name, mode, n, "update_constrained", n, "no_constrained_cols"))

    # 4. update_unconstrained
    try:
        timings = [_time_execute(conn, _update_col_sql(table_name, u_col, u_type)) for _ in range(reps)]
        suite.add(_make_result(table_name, mode, n, "update_unconstrained", timings, n))
    except Exception:
        _reset_conn(conn)
        suite.add(_na_result(table_name, mode, n, "update_unconstrained", n, "failed"))

    # 5. read_constrained
    if c_col:
        try:
            timings = [_time_execute(conn, _read_col_sql(table_name, c_col, c_type)) for _ in range(reps)]
            suite.add(_make_result(table_name, mode, n, "read_constrained", timings, n))
        except Exception:
            _reset_conn(conn)
            suite.add(_na_result(table_name, mode, n, "read_constrained", n, "failed"))
    else:
        suite.add(_na_result(table_name, mode, n, "read_constrained", n, "no_constrained_cols"))

    # 6. read_unconstrained
    try:
        timings = [_time_execute(conn, _read_col_sql(table_name, u_col, u_type)) for _ in range(reps)]
        suite.add(_make_result(table_name, mode, n, "read_unconstrained", timings, n))
    except Exception:
        _reset_conn(conn)
        suite.add(_na_result(table_name, mode, n, "read_unconstrained", n, "failed"))


def run_benchmarks(
    constraint_artifacts: list[tuple[TransformedCheckConstraint, OutputCheck]],
    table_schemas: dict[str, dict[str, str]],
    row_counts: Optional[list[int]] = None,
    exists_row_counts: Optional[list[int]] = None,
    reps: int = DEFAULT_REPS,
    csv_output_path: Optional[str] = None,
) -> BenchmarkSuite:
    """Run performance benchmarks on the parsed constraints from input SQL.
    
    Groups constraints by table, then for each table benchmarks:
    - no_constraint (baseline)
    - trigger (generated triggers from our compiler)
    - native_check (original CHECK from input SQL, NA if unsupported)
    """
    if row_counts is None:
        row_counts = DEFAULT_ROW_COUNTS
    if exists_row_counts is None:
        exists_row_counts = EXISTS_ROW_COUNTS

    # group by table
    tables: dict[str, list[tuple[TransformedCheckConstraint, OutputCheck]]] = {}
    for c, a in constraint_artifacts:
        tables.setdefault(c.table_name, []).append((c, a))

    suite = BenchmarkSuite()
    conn = get_connection()
    conn.autocommit = False

    try:
        _set_schema(conn)

        for table_name, constraints in tables.items():
            schema = table_schemas.get(table_name)
            if not schema:
                log(f"Skipping {table_name} — no schema available (ALTER TABLE?)", LogTag.WARNING)
                continue

            # check if any constraint is EXISTS type
            has_exists = any(isinstance(c.condition, ExistsExpr) for c, _ in constraints)
            counts = exists_row_counts if has_exists else row_counts

            artifacts_list = [a for _, a in constraints]
            constrained, unconstrained = _split_columns(schema, constraints)

            banner(f"Benchmarking table: {table_name} ({len(constraints)} constraints)")
            log(f"constrained cols: {constrained}, unconstrained cols: {unconstrained}", LogTag.INFO)

            for mode in ["no_constraint", "trigger", "native_check"]:
                for n in counts:
                    log(f"{table_name} | mode={mode} | rows={n} | reps={reps}", LogTag.INFO)
                    _reset_conn(conn)
                    _benchmark_table_mode(
                        conn, suite, table_name, schema, mode,
                        constraints, artifacts_list,
                        constrained, unconstrained, n, reps,
                    )

            # cleanup
            _reset_conn(conn)
            cur = conn.cursor()
            cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;") # type: ignore 
            conn.commit()
            cur.close()

    except Exception as e:
        log(f"Benchmark failed: {e}", LogTag.ERROR)
        raise
    finally:
        conn.close()

    suite.print_summary()

    if csv_output_path:
        timestamp = datetime.now().strftime("%d%b_%H%M")
        suite.to_csv(f"log/{timestamp}_{csv_output_path}")
        log(f"Results written to {csv_output_path}", LogTag.INFO)

    return suite
