"""Транспортные сущности (запросы/ответы)."""
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class CreateObservationRequest:
    species_id: int
    location_id: int
    researcher_id: int
    observation_date: date
    individuals_count: int
    notes: Optional[str] = None


@dataclass
class PopulationAnalysisRequest:
    species_id: int
    date_from: date
    date_to: date
    location_id: Optional[int] = None


@dataclass
class PopulationAnalysisResult:
    records_count: int
    has_trend: bool
    rows: list[tuple[date, int]]
    warning_message: Optional[str] = None


@dataclass
class SaveSpeciesRequest:
    scientific_name: str
    common_name: str


@dataclass
class SaveLocationRequest:
    name: str
    region: str = ""


@dataclass
class SaveResearcherRequest:
    full_name: str
    organization: str = ""
