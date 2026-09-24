"""Данные для представлений (View): контроллер не знает про HTML."""
from __future__ import annotations

from dataclasses import dataclass, field


ROLE_RESEARCHER = "researcher"
ROLE_ADMIN = "admin"
ROLE_LABELS = {
    ROLE_RESEARCHER: "Исследователь",
    ROLE_ADMIN: "Администратор",
}


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str


@dataclass(frozen=True)
class CatalogOption:
    id: int
    label: str


@dataclass(frozen=True)
class ObservationRow:
    id: int
    date: str
    species: str
    location: str
    researcher: str
    count: int
    notes: str


@dataclass
class ObservationFormState:
    species: list[CatalogOption]
    locations: list[CatalogOption]
    researchers: list[CatalogOption]
    values: dict[str, str]
    can_submit: bool


@dataclass(frozen=True)
class AnalyticsPoint:
    date: str
    size: int


@dataclass
class PopulationChart:
    line_points: str = ""
    area_points: str = ""
    y_max: int = 0
    x_labels: list[str] = field(default_factory=list)


@dataclass
class AnalyticsState:
    species: list[CatalogOption]
    locations: list[CatalogOption]
    values: dict[str, str]
    records_count: int | None = None
    has_trend: bool | None = None
    warning: str | None = None
    rows: list[AnalyticsPoint] = field(default_factory=list)
    error: str | None = None
    chart: PopulationChart = field(default_factory=PopulationChart)


@dataclass(frozen=True)
class SpeciesRow:
    id: int
    scientific_name: str
    common_name: str


@dataclass
class SpeciesPage:
    rows: list[SpeciesRow]
    editing_id: int | None
    scientific_name: str
    common_name: str


@dataclass(frozen=True)
class LocationRow:
    id: int
    name: str
    region: str


@dataclass(frozen=True)
class ResearcherRow:
    id: int
    full_name: str
    organization: str
