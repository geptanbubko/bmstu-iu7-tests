"""Сравниваемые объекты (targets) и сценарии нагрузки.

Сценарий по seed строит детерминированный план операций: последовательность (функция, аргумент, вид).
Для SQL и ORM план одинаков — одни и те же id, даты и значения в одном и том же порядке.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable

from bench import dataset
from bench.orm_repository import OrmRepository
from wildlife_business.entities import Observation
from wildlife_data.sqlite_repository import SqliteRepository

TARGETS = {
    "sql": "SQL (sqlite3, SqliteRepository)",
    "orm": "ORM (SQLAlchemy 2.0)",
}


def open_target(name: str, database: str):
    if name == "sql":
        return SqliteRepository(database)
    if name == "orm":
        return OrmRepository(database)
    raise ValueError(f"Неизвестная реализация: {name}")


@dataclass(frozen=True)
class Plan:
    """Операции плана: fns[i](args[i]); kinds[i] — вид операции (read / write)."""

    fns: list[Callable[[Any], Any]]
    args: list[Any]
    kinds: list[str]


def _species_ids(rnd: random.Random, n: int) -> list[int]:
    return [rnd.randint(1, dataset.SPECIES) for _ in range(n)]


def _range_queries(rnd: random.Random, n: int, days: int = dataset.RECORD_DAYS) -> list[tuple]:
    queries = []
    for _ in range(n):
        start = dataset.START_DATE + timedelta(days=rnd.randrange(days - 30))
        queries.append(
            (
                rnd.randint(1, dataset.RECORD_SPECIES),
                start,
                start + timedelta(days=29),  # окно 30 дней → до 30 строк
                rnd.randint(1, dataset.RECORD_LOCATIONS),
            )
        )
    return queries


def _observations(rnd: random.Random, n: int) -> list[Observation]:
    return [
        Observation(
            id=None,
            observation_date=dataset.START_DATE + timedelta(days=rnd.randrange(dataset.RECORD_DAYS)),
            individuals_count=rnd.randint(1, 50),
            species_id=rnd.randint(1, dataset.SPECIES),
            location_id=rnd.randint(1, dataset.LOCATIONS),
            researcher_id=rnd.randint(1, dataset.RESEARCHERS),
            notes="bench",
        )
        for _ in range(n)
    ]


def _upserts(rnd: random.Random, n: int) -> list[tuple]:
    return [
        (
            rnd.randint(1, dataset.RECORD_SPECIES),
            rnd.randint(1, dataset.RECORD_LOCATIONS),
            rnd.randint(1, dataset.RESEARCHERS),
            dataset.START_DATE + timedelta(days=rnd.randrange(dataset.UPSERT_DAYS)),
            rnd.randint(10, 5_000),
        )
        for _ in range(n)
    ]


def _read_by_id(repo, rnd: random.Random, n: int) -> Plan:
    fn = repo.get_species
    return Plan([fn] * n, _species_ids(rnd, n), ["read"] * n)


def _read_range(repo, rnd: random.Random, n: int) -> Plan:
    def find(query):
        return repo.find_population_records(*query)

    return Plan([find] * n, _range_queries(rnd, n), ["read"] * n)


def _write_insert(repo, rnd: random.Random, n: int) -> Plan:
    fn = repo.add_observation
    return Plan([fn] * n, _observations(rnd, n), ["write"] * n)


MIXED_WRITE_SHARE = 0.3


def _mixed(repo, rnd: random.Random, n: int) -> Plan:
    """Запись идёт во время чтения: 70 % чтений диапазона и 30 % upsert в ту же таблицу и индекс."""

    def find(query):
        return repo.find_population_records(*query)

    def upsert(values):
        return repo.upsert_population_record(*values)

    # Чтения захватывают оба года: второй год наполняется upsert-ами по ходу прогона.
    reads = iter(_range_queries(rnd, n, dataset.UPSERT_DAYS))
    writes = iter(_upserts(rnd, n))
    fns, args, kinds = [], [], []
    for _ in range(n):
        if rnd.random() < MIXED_WRITE_SHARE:
            fns.append(upsert)
            args.append(next(writes))
            kinds.append("write")
        else:
            fns.append(find)
            args.append(next(reads))
            kinds.append("read")
    return Plan(fns, args, kinds)


@dataclass(frozen=True)
class Scenario:
    name: str
    title: str
    build: Callable[[Any, random.Random, int], Plan]


SCENARIOS = {
    s.name: s
    for s in (
        Scenario("read_by_id", "Чтение вида по первичному ключу (get_species)", _read_by_id),
        Scenario(
            "read_range",
            "Чтение учётов за 30 дней по индексу (find_population_records)",
            _read_range,
        ),
        Scenario("write_insert", "Запись наблюдения (add_observation + commit)", _write_insert),
        Scenario(
            "mixed",
            "Смешанный: 70 % чтений диапазона + 30 % upsert в ту же таблицу",
            _mixed,
        ),
    )
}
