"""Проверка честности сравнения: на одном и том же плане SQL и ORM возвращают одно и то же
и оставляют БД в одинаковом состоянии. Запускается перед замерами (ci/bench.sh, bench.yml)."""
from __future__ import annotations

import os
import random
import shutil
import sqlite3
import tempfile

from bench import dataset
from bench.scenarios import SCENARIOS, open_target

TABLES = ("observations", "population_records", "species")


def _snapshot(database: str) -> dict[str, list[tuple]]:
    conn = sqlite3.connect(database)
    try:
        return {t: conn.execute(f"SELECT * FROM {t} ORDER BY id").fetchall() for t in TABLES}
    finally:
        conn.close()


def _replay(target: str, scenario: str, ops: int, seed: int) -> tuple[list, dict]:
    workdir = tempfile.mkdtemp(prefix="wildlife-verify-", dir=os.environ.get("BENCH_DB_DIR"))
    database = os.path.join(workdir, "verify.db")
    try:
        dataset.seed_database(database)
        repo = open_target(target, database)
        plan = SCENARIOS[scenario].build(repo, random.Random(seed), ops)
        results = [fn(arg) for fn, arg in zip(plan.fns, plan.args)]
        repo.close()
        return results, _snapshot(database)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def verify(ops: int = 300, seed: int = 7) -> list[str]:
    problems = []
    for scenario in SCENARIOS:
        sql_results, sql_db = _replay("sql", scenario, ops, seed)
        orm_results, orm_db = _replay("orm", scenario, ops, seed)
        found = []
        if sql_results != orm_results:
            first = next(i for i, (a, b) in enumerate(zip(sql_results, orm_results)) if a != b)
            found.append(f"{scenario}: результат операции #{first} различается")
        if sql_db != orm_db:
            found.append(f"{scenario}: состояние БД после плана различается")
        problems += found
        print(f"[verify] {scenario:<12} {ops} оп.: {'; '.join(found) or 'OK'}")
    return problems
