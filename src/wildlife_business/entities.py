"""Системные сущности (domain)."""
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Species:
    id: Optional[int]
    scientific_name: str
    common_name: str


@dataclass
class Observation:
    id: Optional[int]
    observation_date: date
    individuals_count: int
    species_id: int
    location_id: int
    researcher_id: int
    notes: Optional[str] = None


@dataclass
class Location:
    id: Optional[int]
    name: str
    region: Optional[str] = None


@dataclass
class Researcher:
    id: Optional[int]
    full_name: str
    organization: Optional[str] = None


@dataclass
class PopulationRecord:
    record_date: date
    population_size: int
