"""Data Builder: запрос с разумными значениями по умолчанию, тест меняет только важное поле."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Optional

from wildlife_business.dto import CreateObservationRequest


@dataclass(frozen=True)
class ObservationRequestBuilder:
    """Неизменяемый builder: каждый with_* возвращает новую копию, исходный не меняется."""

    species_id: int = 1
    location_id: int = 2
    researcher_id: int = 3
    observation_date: date = date(2026, 3, 1)
    individuals_count: int = 7
    notes: Optional[str] = None

    def for_refs(self, species_id: int, location_id: int, researcher_id: int) -> ObservationRequestBuilder:
        return replace(
            self, species_id=species_id, location_id=location_id, researcher_id=researcher_id
        )

    def with_species(self, species_id: int) -> ObservationRequestBuilder:
        return replace(self, species_id=species_id)

    def with_location(self, location_id: int) -> ObservationRequestBuilder:
        return replace(self, location_id=location_id)

    def with_researcher(self, researcher_id: int) -> ObservationRequestBuilder:
        return replace(self, researcher_id=researcher_id)

    def on(self, observation_date: date) -> ObservationRequestBuilder:
        return replace(self, observation_date=observation_date)

    def with_count(self, individuals_count: int) -> ObservationRequestBuilder:
        return replace(self, individuals_count=individuals_count)

    def with_notes(self, notes: Optional[str]) -> ObservationRequestBuilder:
        return replace(self, notes=notes)

    def build(self) -> CreateObservationRequest:
        return CreateObservationRequest(
            species_id=self.species_id,
            location_id=self.location_id,
            researcher_id=self.researcher_id,
            observation_date=self.observation_date,
            individuals_count=self.individuals_count,
            notes=self.notes,
        )


def an_observation() -> ObservationRequestBuilder:
    """Точка входа: an_observation().with_count(-4).build()."""
    return ObservationRequestBuilder()
