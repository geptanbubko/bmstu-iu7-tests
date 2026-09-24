"""Контракт доступа к данным. Задаётся бизнес-логикой (DIP), реализация — wildlife_data."""
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from wildlife_business.entities import Location, Observation, PopulationRecord, Researcher, Species


class IRepository(ABC):
    @abstractmethod
    def add_observation(self, observation: Observation) -> Observation:
        pass

    @abstractmethod
    def list_observations(self) -> list[Observation]:
        pass

    @abstractmethod
    def find_population_records(
        self,
        species_id: int,
        date_from: date,
        date_to: date,
        location_id: Optional[int] = None,
    ) -> list[PopulationRecord]:
        pass

    @abstractmethod
    def upsert_population_record(
        self,
        species_id: int,
        location_id: int,
        researcher_id: int,
        record_date: date,
        population_size: int,
    ) -> None:
        pass

    @abstractmethod
    def save_species(self, species: Species) -> Species:
        pass

    @abstractmethod
    def get_species(self, species_id: int) -> Optional[Species]:
        pass

    @abstractmethod
    def update_species(self, species: Species) -> Species:
        pass

    @abstractmethod
    def delete_species(self, species_id: int) -> None:
        pass

    @abstractmethod
    def species_exists(self, scientific_name: str) -> bool:
        pass

    @abstractmethod
    def list_species(self) -> list[Species]:
        pass

    @abstractmethod
    def save_location(self, location: Location) -> Location:
        pass

    @abstractmethod
    def list_locations(self) -> list[Location]:
        pass

    @abstractmethod
    def save_researcher(self, researcher: Researcher) -> Researcher:
        pass

    @abstractmethod
    def list_researchers(self) -> list[Researcher]:
        pass
