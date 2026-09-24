"""Контроллеры MVC: сценарии GUI над теми же сервисами, что и консоль."""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from typing import TypeVar

from wildlife_business.analytics_service import AnalyticsService
from wildlife_business.catalog_service import CatalogService
from wildlife_business.exceptions import BusinessError
from wildlife_business.observation_service import ObservationService
from wildlife_gui.chart import build_population_chart
from wildlife_gui.forms import (
    form_values,
    parse_analytics_form,
    parse_location_form,
    parse_observation_form,
    parse_researcher_form,
    parse_species_form,
)
from wildlife_gui.viewmodels import (
    ROLE_ADMIN,
    ROLE_LABELS,
    ROLE_RESEARCHER,
    ActionResult,
    AnalyticsPoint,
    AnalyticsState,
    CatalogOption,
    LocationRow,
    ObservationFormState,
    ObservationRow,
    ResearcherRow,
    SpeciesPage,
    SpeciesRow,
)

logger = logging.getLogger("wildlife.gui")

T = TypeVar("T")


def _options(items: Iterable[T], label_of: Callable[[T], str]) -> list[CatalogOption]:
    return [CatalogOption(item.id, label_of(item)) for item in items if getattr(item, "id", None)]


class RoleController:
    def select(self, role: str) -> ActionResult:
        if role not in ROLE_LABELS:
            logger.warning("Неизвестная роль GUI: %s", role)
            return ActionResult(False, "Неизвестная роль")
        logger.info("Пользователь выбрал роль: %s", ROLE_LABELS[role].lower())
        return ActionResult(True, f"Роль: {ROLE_LABELS[role]}")

    @staticmethod
    def label(role: str | None) -> str:
        return ROLE_LABELS.get(role or "", "не выбрана")


class ObservationController:
    def __init__(self, observations: ObservationService, catalog: CatalogService) -> None:
        self._observations = observations
        self._catalog = catalog

    def list_rows(self) -> list[ObservationRow]:
        species = {item.id: item for item in self._catalog.list_species()}
        locations = {item.id: item for item in self._catalog.list_locations()}
        researchers = {item.id: item for item in self._catalog.list_researchers()}
        rows: list[ObservationRow] = []
        for item in self._observations.list_observations():
            spec = species.get(item.species_id)
            loc = locations.get(item.location_id)
            res = researchers.get(item.researcher_id)
            rows.append(
                ObservationRow(
                    id=item.id or 0,
                    date=item.observation_date.isoformat(),
                    species=(
                        f"{spec.scientific_name} ({spec.common_name})"
                        if spec
                        else str(item.species_id)
                    ),
                    location=loc.name if loc else str(item.location_id),
                    researcher=res.full_name if res else str(item.researcher_id),
                    count=item.individuals_count,
                    notes=item.notes or "",
                )
            )
        return rows

    def form_state(self, values: Mapping[str, str] | None = None) -> ObservationFormState:
        species = _options(
            self._catalog.list_species(),
            lambda item: f"{item.scientific_name} ({item.common_name})",
        )
        locations = _options(self._catalog.list_locations(), lambda item: item.name)
        researchers = _options(self._catalog.list_researchers(), lambda item: item.full_name)
        return ObservationFormState(
            species=species,
            locations=locations,
            researchers=researchers,
            values=dict(values or {}),
            can_submit=bool(species and locations and researchers),
        )

    def create(self, data: Mapping[str, str]) -> ActionResult:
        try:
            saved = self._observations.create_observation(parse_observation_form(data))
        except BusinessError as exc:
            logger.warning("Исключение бизнес-логики: %s", exc, exc_info=True)
            return ActionResult(False, str(exc))
        logger.info(
            "Пользователь добавил наблюдение id=%s species=%s location=%s count=%s",
            saved.id,
            saved.species_id,
            saved.location_id,
            saved.individuals_count,
        )
        return ActionResult(True, f"Наблюдение сохранено, id={saved.id}")


class AnalyticsController:
    def __init__(self, analytics: AnalyticsService, catalog: CatalogService) -> None:
        self._analytics = analytics
        self._catalog = catalog

    def page(self, data: Mapping[str, str] | None = None) -> AnalyticsState:
        species = _options(
            self._catalog.list_species(),
            lambda item: f"{item.scientific_name} ({item.common_name})",
        )
        locations = _options(self._catalog.list_locations(), lambda item: item.name)
        values = form_values(
            data or {}, "species_id", "location_id", "date_from", "date_to"
        )
        state = AnalyticsState(species=species, locations=locations, values=values)
        if data is None:
            return state
        try:
            result = self._analytics.analyze_population(parse_analytics_form(data))
        except BusinessError as exc:
            logger.warning("Исключение бизнес-логики: %s", exc, exc_info=True)
            state.error = str(exc)
            return state
        logger.info(
            "Пользователь запросил аналитику species=%s from=%s to=%s records=%s",
            values.get("species_id"),
            values.get("date_from"),
            values.get("date_to"),
            result.records_count,
        )
        state.records_count = result.records_count
        state.has_trend = result.has_trend
        state.warning = result.warning_message
        state.rows = [AnalyticsPoint(d.isoformat(), size) for d, size in result.rows]
        state.chart = build_population_chart(state.rows)
        return state


class CatalogController:
    def __init__(self, catalog: CatalogService) -> None:
        self._catalog = catalog

    def species_page(self, editing_id: int | None = None) -> SpeciesPage:
        rows = [
            SpeciesRow(item.id or 0, item.scientific_name, item.common_name)
            for item in self._catalog.list_species()
        ]
        scientific = common = ""
        found_id = None
        if editing_id is not None:
            match = next((row for row in rows if row.id == editing_id), None)
            if match is not None:
                found_id = match.id
                scientific = match.scientific_name
                common = match.common_name
        return SpeciesPage(rows, found_id, scientific, common)

    def add_species(self, data: Mapping[str, str]) -> ActionResult:
        try:
            saved = self._catalog.add_species(parse_species_form(data))
        except BusinessError as exc:
            logger.warning("Исключение бизнес-логики: %s", exc, exc_info=True)
            return ActionResult(False, str(exc))
        logger.info("Пользователь добавил вид id=%s (%s)", saved.id, saved.scientific_name)
        return ActionResult(True, f"Вид сохранён, id={saved.id} ({saved.scientific_name})")

    def update_species(self, species_id: int, data: Mapping[str, str]) -> ActionResult:
        try:
            updated = self._catalog.update_species(species_id, parse_species_form(data))
        except BusinessError as exc:
            logger.warning("Исключение бизнес-логики: %s", exc, exc_info=True)
            return ActionResult(False, str(exc))
        logger.info("Пользователь изменил вид id=%s", species_id)
        return ActionResult(
            True, f"Вид изменён: {updated.scientific_name} / {updated.common_name}"
        )

    def list_locations(self) -> list[LocationRow]:
        return [
            LocationRow(item.id or 0, item.name, item.region or "")
            for item in self._catalog.list_locations()
        ]

    def add_location(self, data: Mapping[str, str]) -> ActionResult:
        try:
            saved = self._catalog.add_location(parse_location_form(data))
        except BusinessError as exc:
            logger.warning("Исключение бизнес-логики: %s", exc, exc_info=True)
            return ActionResult(False, str(exc))
        logger.info("Пользователь добавил локацию id=%s (%s)", saved.id, saved.name)
        return ActionResult(True, f"Локация сохранена, id={saved.id} ({saved.name})")

    def list_researchers(self) -> list[ResearcherRow]:
        return [
            ResearcherRow(item.id or 0, item.full_name, item.organization or "")
            for item in self._catalog.list_researchers()
        ]

    def add_researcher(self, data: Mapping[str, str]) -> ActionResult:
        try:
            saved = self._catalog.add_researcher(parse_researcher_form(data))
        except BusinessError as exc:
            logger.warning("Исключение бизнес-логики: %s", exc, exc_info=True)
            return ActionResult(False, str(exc))
        logger.info("Пользователь добавил исследователя id=%s", saved.id)
        return ActionResult(True, f"Исследователь сохранён, id={saved.id} ({saved.full_name})")


__all__ = [
    "ROLE_ADMIN",
    "ROLE_RESEARCHER",
    "AnalyticsController",
    "CatalogController",
    "ObservationController",
    "RoleController",
]
