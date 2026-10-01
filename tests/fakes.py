"""In-memory fake of IRepository: not SQLite and not an in-memory database."""
from __future__ import annotations

from datetime import date
from typing import Optional

from wildlife_business.entities import Location, Observation, PopulationRecord, Researcher, Species
from wildlife_business.repository import IRepository
from wildlife_data.exceptions import DuplicateEntityError, EntityNotFoundError, IntegrityConstraintError


class FakeRepository(IRepository):
    def __init__(self) -> None:
        self._species: dict[int, Species] = {}
        self._locations: dict[int, Location] = {}
        self._researchers: dict[int, Researcher] = {}
        self._observations: dict[int, Observation] = {}
        self._population: dict[tuple[int, int, date], tuple[int, int]] = {}
        self._next_id = 1

    def _alloc_id(self) -> int:
        allocated = self._next_id
        self._next_id += 1
        return allocated

    def add_observation(self, observation: Observation) -> Observation:
        self._require_fk(observation.species_id, observation.location_id, observation.researcher_id)
        saved = Observation(
            id=self._alloc_id(),
            observation_date=observation.observation_date,
            individuals_count=observation.individuals_count,
            species_id=observation.species_id,
            location_id=observation.location_id,
            researcher_id=observation.researcher_id,
            notes=observation.notes,
        )
        self._observations[saved.id] = saved
        return saved

    def list_observations(self) -> list[Observation]:
        return sorted(self._observations.values(), key=lambda row: (row.observation_date, row.id or 0))

    def find_population_records(
        self,
        species_id: int,
        date_from: date,
        date_to: date,
        location_id: Optional[int] = None,
    ) -> list[PopulationRecord]:
        rows: list[PopulationRecord] = []
        for (sid, lid, record_date), (size, _researcher_id) in self._population.items():
            if sid != species_id:
                continue
            if location_id is not None and lid != location_id:
                continue
            if date_from <= record_date <= date_to:
                rows.append(PopulationRecord(record_date, size))
        return sorted(rows, key=lambda row: row.record_date)

    def upsert_population_record(
        self,
        species_id: int,
        location_id: int,
        researcher_id: int,
        record_date: date,
        population_size: int,
    ) -> None:
        self._require_fk(species_id, location_id, researcher_id)
        self._population[(species_id, location_id, record_date)] = (population_size, researcher_id)

    def save_species(self, species: Species) -> Species:
        name = species.scientific_name.strip()
        if any(row.scientific_name == name for row in self._species.values()):
            raise DuplicateEntityError("Вид с таким научным названием уже существует")
        saved = Species(self._alloc_id(), name, species.common_name.strip())
        self._species[saved.id] = saved
        return saved

    def get_species(self, species_id: int) -> Optional[Species]:
        return self._species.get(species_id)

    def update_species(self, species: Species) -> Species:
        if species.id is None or species.id not in self._species:
            raise EntityNotFoundError(f"Вид id={species.id} не найден")
        updated = Species(species.id, species.scientific_name.strip(), species.common_name.strip())
        self._species[species.id] = updated
        return updated

    def delete_species(self, species_id: int) -> None:
        if species_id not in self._species:
            raise EntityNotFoundError(f"Вид id={species_id} не найден")
        del self._species[species_id]

    def species_exists(self, scientific_name: str) -> bool:
        name = scientific_name.strip()
        return any(row.scientific_name == name for row in self._species.values())

    def list_species(self) -> list[Species]:
        return [self._species[key] for key in sorted(self._species)]

    def save_location(self, location: Location) -> Location:
        saved = Location(self._alloc_id(), location.name.strip(), location.region)
        self._locations[saved.id] = saved
        return saved

    def list_locations(self) -> list[Location]:
        return [self._locations[key] for key in sorted(self._locations)]

    def save_researcher(self, researcher: Researcher) -> Researcher:
        saved = Researcher(self._alloc_id(), researcher.full_name.strip(), researcher.organization)
        self._researchers[saved.id] = saved
        return saved

    def list_researchers(self) -> list[Researcher]:
        return [self._researchers[key] for key in sorted(self._researchers)]

    def _require_fk(self, species_id: int, location_id: int, researcher_id: int) -> None:
        if species_id not in self._species or location_id not in self._locations or researcher_id not in self._researchers:
            raise IntegrityConstraintError("Нарушение ссылочной целостности")
