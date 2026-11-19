"""ORM-реализация тех же операций, что и у SqliteRepository (SQLAlchemy 2.x).

Отображает существующие таблицы (схема создаётся wildlife_data.schema), валидирует вход теми же
правилами, что и SQL-репозиторий, и возвращает те же доменные dataclass-ы — сравниваются
только способы доступа к данным: «SQL руками через sqlite3» против «ORM поверх того же драйвера».

Сессия открывается на каждую операцию (unit of work на запрос — типичный способ работы с ORM),
соединение берётся из пула движка, поэтому, как и у SqliteRepository, не переоткрывается.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, create_engine, event, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from wildlife_business.entities import Observation, PopulationRecord, Species
from wildlife_data.exceptions import DataValidationError
from wildlife_data.sqlite_repository import SqliteRepository


class Base(DeclarativeBase):
    pass


class SpeciesRow(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scientific_name: Mapped[str] = mapped_column(String, unique=True)
    common_name: Mapped[str] = mapped_column(String)
    conservation_status: Mapped[Optional[str]]
    description: Mapped[Optional[str]]


class ObservationRow(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    observation_date: Mapped[str] = mapped_column(String)
    individuals_count: Mapped[int]
    notes: Mapped[Optional[str]]
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    researcher_id: Mapped[int] = mapped_column(ForeignKey("researchers.id"))


class PopulationRecordRow(Base):
    __tablename__ = "population_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_date: Mapped[str] = mapped_column(String)
    population_size: Mapped[int]
    method: Mapped[Optional[str]]
    notes: Mapped[Optional[str]]
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    researcher_id: Mapped[int] = mapped_column(ForeignKey("researchers.id"))


# Таблицы researchers/locations нужны только как цели внешних ключей.
class _ResearcherRow(Base):
    __tablename__ = "researchers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class _LocationRow(Base):
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class OrmRepository:
    """Подмножество IRepository, которое участвует в бенчмарке."""

    def __init__(self, database: str) -> None:
        self._engine = create_engine(f"sqlite:///{database}")

        @event.listens_for(self._engine, "connect")
        def _pragmas(dbapi_connection, _record):  # те же настройки соединения, что у SQL
            dbapi_connection.execute("PRAGMA foreign_keys = ON")

        self._sessions = sessionmaker(self._engine, expire_on_commit=False)

    def close(self) -> None:
        self._engine.dispose()

    def get_species(self, species_id: int) -> Optional[Species]:
        SqliteRepository._require_positive_id(species_id, "вида")
        with self._sessions() as session:
            row = session.scalars(
                select(SpeciesRow).where(SpeciesRow.id == species_id)
            ).one_or_none()
            if row is None:
                return None
            return Species(row.id, row.scientific_name, row.common_name)

    def add_observation(self, observation: Observation) -> Observation:
        SqliteRepository._validate_observation(observation)
        row = ObservationRow(
            observation_date=observation.observation_date.isoformat(),
            individuals_count=observation.individuals_count,
            notes=observation.notes,
            species_id=observation.species_id,
            location_id=observation.location_id,
            researcher_id=observation.researcher_id,
        )
        with self._sessions() as session:
            session.add(row)
            session.commit()
        return Observation(
            id=row.id,
            observation_date=observation.observation_date,
            individuals_count=observation.individuals_count,
            species_id=observation.species_id,
            location_id=observation.location_id,
            researcher_id=observation.researcher_id,
            notes=observation.notes,
        )

    def upsert_population_record(
        self,
        species_id: int,
        location_id: int,
        researcher_id: int,
        record_date: date,
        population_size: int,
    ) -> None:
        SqliteRepository._require_positive_id(species_id, "вида")
        SqliteRepository._require_positive_id(location_id, "локации")
        SqliteRepository._require_positive_id(researcher_id, "исследователя")
        if population_size < 0:
            raise DataValidationError("Численность не может быть отрицательной")
        # Тот же INSERT … ON CONFLICT DO UPDATE, что и в SQL-репозитории, но собранный ORM.
        statement = sqlite_insert(PopulationRecordRow).values(
            record_date=record_date.isoformat(),
            population_size=population_size,
            species_id=species_id,
            location_id=location_id,
            researcher_id=researcher_id,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["species_id", "location_id", "record_date"],
            set_={
                "population_size": statement.excluded.population_size,
                "researcher_id": statement.excluded.researcher_id,
            },
        )
        with self._sessions() as session:
            session.execute(statement)
            session.commit()

    def find_population_records(
        self,
        species_id: int,
        date_from: date,
        date_to: date,
        location_id: Optional[int] = None,
    ) -> list[PopulationRecord]:
        SqliteRepository._require_positive_id(species_id, "вида")
        if date_from > date_to:
            raise DataValidationError("Дата начала периода не может быть позже даты окончания")
        query = select(PopulationRecordRow).where(
            PopulationRecordRow.species_id == species_id,
            PopulationRecordRow.record_date.between(date_from.isoformat(), date_to.isoformat()),
        )
        if location_id is not None:
            SqliteRepository._require_positive_id(location_id, "локации")
            query = query.where(PopulationRecordRow.location_id == location_id)
        query = query.order_by(PopulationRecordRow.record_date)
        with self._sessions() as session:
            return [
                PopulationRecord(
                    record_date=date.fromisoformat(row.record_date),
                    population_size=row.population_size,
                )
                for row in session.scalars(query)
            ]
