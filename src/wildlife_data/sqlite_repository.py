"""Реализация IRepository на SQLite: SQL без ORM, персистентное хранение."""
from __future__ import annotations

import sqlite3
import threading
from datetime import date
from pathlib import Path
from typing import NoReturn, Optional, Union

from wildlife_business.entities import Location, Observation, PopulationRecord, Researcher, Species
from wildlife_data.exceptions import (
    DataAccessError,
    DataValidationError,
    DuplicateEntityError,
    EntityNotFoundError,
    IntegrityConstraintError,
)
from wildlife_data.schema import SCHEMA_SQL
from wildlife_business.repository import IRepository

DatabasePath = Union[str, Path]


class SqliteRepository(IRepository):
    def __init__(self, database: DatabasePath) -> None:
        self._database = str(database)
        self._local = threading.local()
        self._conn

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._database)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript(SCHEMA_SQL)
            conn.commit()
            self._local.conn = conn
        return conn

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    def __enter__(self) -> SqliteRepository:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def save_species(self, species: Species) -> Species:
        if species.id is not None:
            raise DataValidationError("Для создания вида идентификатор задавать не нужно")
        name, common = self._validated_species_names(species)
        try:
            cursor = self._conn.execute(
                "INSERT INTO species (scientific_name, common_name) VALUES (?, ?)",
                (name, common),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            self._conn.rollback()
            self._raise_integrity(exc)
        except sqlite3.Error as exc:
            self._conn.rollback()
            raise DataAccessError("Не удалось сохранить вид") from exc
        return Species(cursor.lastrowid, name, common)

    def get_species(self, species_id: int) -> Optional[Species]:
        self._require_positive_id(species_id, "вида")
        row = self._conn.execute(
            "SELECT id, scientific_name, common_name FROM species WHERE id = ?",
            (species_id,),
        ).fetchone()
        return None if row is None else self._row_to_species(row)

    def update_species(self, species: Species) -> Species:
        if species.id is None:
            raise DataValidationError("Для изменения вида нужен идентификатор")
        self._require_positive_id(species.id, "вида")
        name, common = self._validated_species_names(species)
        if self.get_species(species.id) is None:
            raise EntityNotFoundError(f"Вид id={species.id} не найден")
        try:
            self._conn.execute(
                "UPDATE species SET scientific_name = ?, common_name = ? WHERE id = ?",
                (name, common, species.id),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            self._conn.rollback()
            self._raise_integrity(exc)
        except sqlite3.Error as exc:
            self._conn.rollback()
            raise DataAccessError("Не удалось изменить вид") from exc
        return Species(species.id, name, common)

    def delete_species(self, species_id: int) -> None:
        self._require_positive_id(species_id, "вида")
        try:
            cursor = self._conn.execute("DELETE FROM species WHERE id = ?", (species_id,))
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            self._conn.rollback()
            self._raise_integrity(exc)
        except sqlite3.Error as exc:
            self._conn.rollback()
            raise DataAccessError("Не удалось удалить вид") from exc
        if cursor.rowcount == 0:
            raise EntityNotFoundError(f"Вид id={species_id} не найден")

    def species_exists(self, scientific_name: str) -> bool:
        name = scientific_name.strip()
        if not name:
            raise DataValidationError("Научное название не может быть пустым")
        row = self._conn.execute(
            "SELECT 1 FROM species WHERE scientific_name = ? LIMIT 1",
            (name,),
        ).fetchone()
        return row is not None

    def add_observation(self, observation: Observation) -> Observation:
        self._validate_observation(observation)
        try:
            cursor = self._conn.execute(
                """
                INSERT INTO observations (
                    observation_date, individuals_count, notes,
                    species_id, location_id, researcher_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    observation.observation_date.isoformat(),
                    observation.individuals_count,
                    observation.notes,
                    observation.species_id,
                    observation.location_id,
                    observation.researcher_id,
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            self._conn.rollback()
            self._raise_integrity(exc)
        except sqlite3.Error as exc:
            self._conn.rollback()
            raise DataAccessError("Не удалось сохранить наблюдение") from exc
        return Observation(
            id=cursor.lastrowid,
            observation_date=observation.observation_date,
            individuals_count=observation.individuals_count,
            species_id=observation.species_id,
            location_id=observation.location_id,
            researcher_id=observation.researcher_id,
            notes=observation.notes,
        )

    def list_observations(self) -> list[Observation]:
        rows = self._conn.execute(
            """
            SELECT id, observation_date, individuals_count, notes,
                   species_id, location_id, researcher_id
            FROM observations
            ORDER BY observation_date, id
            """
        ).fetchall()
        return [
            Observation(
                id=row["id"],
                observation_date=date.fromisoformat(row["observation_date"]),
                individuals_count=row["individuals_count"],
                species_id=row["species_id"],
                location_id=row["location_id"],
                researcher_id=row["researcher_id"],
                notes=row["notes"],
            )
            for row in rows
        ]

    def upsert_population_record(
        self,
        species_id: int,
        location_id: int,
        researcher_id: int,
        record_date: date,
        population_size: int,
    ) -> None:
        self._require_positive_id(species_id, "вида")
        self._require_positive_id(location_id, "локации")
        self._require_positive_id(researcher_id, "исследователя")
        if population_size < 0:
            raise DataValidationError("Численность не может быть отрицательной")
        try:
            self._conn.execute(
                """
                INSERT INTO population_records (
                    record_date, population_size, species_id, location_id, researcher_id
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(species_id, location_id, record_date)
                DO UPDATE SET
                    population_size = excluded.population_size,
                    researcher_id = excluded.researcher_id
                """,
                (
                    record_date.isoformat(),
                    population_size,
                    species_id,
                    location_id,
                    researcher_id,
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            self._conn.rollback()
            self._raise_integrity(exc)
        except sqlite3.Error as exc:
            self._conn.rollback()
            raise DataAccessError("Не удалось сохранить учёт численности") from exc

    def list_species(self) -> list[Species]:
        rows = self._conn.execute(
            "SELECT id, scientific_name, common_name FROM species ORDER BY id"
        ).fetchall()
        return [self._row_to_species(row) for row in rows]

    def save_location(self, location: Location) -> Location:
        if location.id is not None:
            raise DataValidationError("Для создания локации идентификатор задавать не нужно")
        name = location.name.strip()
        if not name:
            raise DataValidationError("Название локации не может быть пустым")
        region = (location.region or "").strip() or None
        try:
            cursor = self._conn.execute(
                "INSERT INTO locations (name, region) VALUES (?, ?)",
                (name, region),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            self._conn.rollback()
            raise DataAccessError("Не удалось сохранить локацию") from exc
        return Location(cursor.lastrowid, name, region)

    def list_locations(self) -> list[Location]:
        rows = self._conn.execute(
            "SELECT id, name, region FROM locations ORDER BY id"
        ).fetchall()
        return [Location(row["id"], row["name"], row["region"]) for row in rows]

    def save_researcher(self, researcher: Researcher) -> Researcher:
        if researcher.id is not None:
            raise DataValidationError(
                "Для создания исследователя идентификатор задавать не нужно"
            )
        full_name = researcher.full_name.strip()
        if not full_name:
            raise DataValidationError("ФИО исследователя не может быть пустым")
        organization = (researcher.organization or "").strip() or None
        try:
            cursor = self._conn.execute(
                "INSERT INTO researchers (full_name, organization) VALUES (?, ?)",
                (full_name, organization),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            self._conn.rollback()
            raise DataAccessError("Не удалось сохранить исследователя") from exc
        return Researcher(cursor.lastrowid, full_name, organization)

    def list_researchers(self) -> list[Researcher]:
        rows = self._conn.execute(
            "SELECT id, full_name, organization FROM researchers ORDER BY id"
        ).fetchall()
        return [
            Researcher(row["id"], row["full_name"], row["organization"]) for row in rows
        ]

    def find_population_records(
        self,
        species_id: int,
        date_from: date,
        date_to: date,
        location_id: Optional[int] = None,
    ) -> list[PopulationRecord]:
        self._require_positive_id(species_id, "вида")
        if date_from > date_to:
            raise DataValidationError(
                "Дата начала периода не может быть позже даты окончания"
            )
        if location_id is not None:
            self._require_positive_id(location_id, "локации")
            rows = self._conn.execute(
                """
                SELECT record_date, population_size
                FROM population_records
                WHERE species_id = ?
                  AND record_date BETWEEN ? AND ?
                  AND location_id = ?
                ORDER BY record_date
                """,
                (species_id, date_from.isoformat(), date_to.isoformat(), location_id),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT record_date, population_size
                FROM population_records
                WHERE species_id = ?
                  AND record_date BETWEEN ? AND ?
                ORDER BY record_date
                """,
                (species_id, date_from.isoformat(), date_to.isoformat()),
            ).fetchall()
        return [
            PopulationRecord(
                record_date=date.fromisoformat(row["record_date"]),
                population_size=row["population_size"],
            )
            for row in rows
        ]

    @staticmethod
    def _row_to_species(row: sqlite3.Row) -> Species:
        return Species(row["id"], row["scientific_name"], row["common_name"])

    @staticmethod
    def _validated_species_names(species: Species) -> tuple[str, str]:
        name = species.scientific_name.strip()
        common = species.common_name.strip()
        if not name or not common:
            raise DataValidationError("Заполните научное и обычное название вида")
        return name, common

    @staticmethod
    def _require_positive_id(value: int, entity: str) -> None:
        if value <= 0:
            raise DataValidationError(f"Некорректный идентификатор {entity}")

    @staticmethod
    def _validate_observation(observation: Observation) -> None:
        if observation.species_id <= 0:
            raise DataValidationError("Укажите вид животного")
        if observation.location_id <= 0:
            raise DataValidationError("Укажите локацию")
        if observation.researcher_id <= 0:
            raise DataValidationError("Укажите исследователя")
        if observation.individuals_count < 0:
            raise DataValidationError("Количество особей не может быть отрицательным")

    @staticmethod
    def _raise_integrity(exc: sqlite3.IntegrityError) -> NoReturn:
        message = str(exc).lower()
        if "unique" in message:
            raise DuplicateEntityError(
                "Вид с таким научным названием уже существует"
            ) from exc
        if "foreign" in message:
            raise IntegrityConstraintError(
                "Нарушение ссылочной целостности"
            ) from exc
        raise IntegrityConstraintError("Нарушение ограничения целостности") from exc
