"""Одинаковый для обеих реализаций начальный набор данных.

БД создаётся «с нуля» на каждый прогон (схема — wildlife_data.schema), заполняется детерминированно
и одинаково для SQL и ORM, поэтому реализации работают с байт-в-байт одинаковым хранилищем.
"""
from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta

from wildlife_data.schema import SCHEMA_SQL

SPECIES = 200
LOCATIONS = 20
RESEARCHERS = 10
OBSERVATIONS = 5_000

# Учёты численности: виды 1..RECORD_SPECIES × локации 1..RECORD_LOCATIONS × каждый день года.
RECORD_SPECIES = 50
RECORD_LOCATIONS = 10
RECORD_DAYS = 365
START_DATE = date(2025, 1, 1)
# Сценарии записи учётов захватывают и второй год: там ключи сначала вставляются, потом обновляются.
UPSERT_DAYS = 2 * RECORD_DAYS


def seed_database(path: str, seed: int = 42) -> dict[str, int]:
    rnd = random.Random(seed)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.executemany(
            "INSERT INTO researchers (full_name, organization) VALUES (?, ?)",
            [(f"Исследователь {i}", f"Заповедник {i % 3}") for i in range(1, RESEARCHERS + 1)],
        )
        conn.executemany(
            "INSERT INTO locations (name, region) VALUES (?, ?)",
            [(f"Локация {i}", f"Регион {i % 5}") for i in range(1, LOCATIONS + 1)],
        )
        conn.executemany(
            "INSERT INTO species (scientific_name, common_name) VALUES (?, ?)",
            [(f"Species scientifica {i}", f"Вид {i}") for i in range(1, SPECIES + 1)],
        )
        conn.executemany(
            """INSERT INTO observations (observation_date, individuals_count, notes,
                   species_id, location_id, researcher_id) VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (
                    (START_DATE + timedelta(days=rnd.randrange(RECORD_DAYS))).isoformat(),
                    rnd.randint(1, 50),
                    None,
                    rnd.randint(1, SPECIES),
                    rnd.randint(1, LOCATIONS),
                    rnd.randint(1, RESEARCHERS),
                )
                for _ in range(OBSERVATIONS)
            ],
        )
        conn.executemany(
            """INSERT INTO population_records (record_date, population_size,
                   species_id, location_id, researcher_id) VALUES (?, ?, ?, ?, ?)""",
            (
                (
                    (START_DATE + timedelta(days=day)).isoformat(),
                    rnd.randint(10, 5_000),
                    species_id,
                    location_id,
                    1 + (species_id + location_id) % RESEARCHERS,
                )
                for species_id in range(1, RECORD_SPECIES + 1)
                for location_id in range(1, RECORD_LOCATIONS + 1)
                for day in range(RECORD_DAYS)
            ),
        )
        conn.commit()
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("researchers", "locations", "species", "observations", "population_records")
        }
    finally:
        conn.close()
    return counts
