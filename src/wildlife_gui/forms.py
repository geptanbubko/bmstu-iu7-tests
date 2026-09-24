"""Разбор форм GUI → DTO бизнес-логики (связующий слой, не HTTP)."""
from __future__ import annotations

from datetime import date
from typing import Mapping

from wildlife_business.dto import (
    CreateObservationRequest,
    PopulationAnalysisRequest,
    SaveLocationRequest,
    SaveResearcherRequest,
    SaveSpeciesRequest,
)
from wildlife_business.exceptions import ValidationError


def form_text(data: Mapping[str, str], key: str) -> str:
    return (data.get(key) or "").strip()


def form_values(data: Mapping[str, str], *keys: str) -> dict[str, str]:
    return {key: form_text(data, key) for key in keys}


def form_int(data: Mapping[str, str], key: str, field: str) -> int:
    raw = form_text(data, key)
    if not raw:
        raise ValidationError(f"Укажите {field}")
    try:
        return int(raw)
    except ValueError as exc:
        raise ValidationError(f"{field}: введите целое число") from exc


def form_optional_int(data: Mapping[str, str], key: str, field: str) -> int | None:
    if not form_text(data, key):
        return None
    return form_int(data, key, field)


def form_date(data: Mapping[str, str], key: str, field: str) -> date:
    raw = form_text(data, key)
    if not raw:
        raise ValidationError(f"Укажите {field}")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError(f"{field}: дата в формате ГГГГ-ММ-ДД") from exc


def parse_observation_form(data: Mapping[str, str]) -> CreateObservationRequest:
    notes = form_text(data, "notes") or None
    return CreateObservationRequest(
        species_id=form_int(data, "species_id", "вид"),
        location_id=form_int(data, "location_id", "локация"),
        researcher_id=form_int(data, "researcher_id", "исследователь"),
        observation_date=form_date(data, "observation_date", "дата"),
        individuals_count=form_int(data, "individuals_count", "количество"),
        notes=notes,
    )


def parse_analytics_form(data: Mapping[str, str]) -> PopulationAnalysisRequest:
    return PopulationAnalysisRequest(
        species_id=form_int(data, "species_id", "вид"),
        date_from=form_date(data, "date_from", "дата начала"),
        date_to=form_date(data, "date_to", "дата окончания"),
        location_id=form_optional_int(data, "location_id", "локация"),
    )


def parse_species_form(data: Mapping[str, str]) -> SaveSpeciesRequest:
    return SaveSpeciesRequest(
        scientific_name=form_text(data, "scientific_name"),
        common_name=form_text(data, "common_name"),
    )


def parse_location_form(data: Mapping[str, str]) -> SaveLocationRequest:
    return SaveLocationRequest(
        name=form_text(data, "name"),
        region=form_text(data, "region"),
    )


def parse_researcher_form(data: Mapping[str, str]) -> SaveResearcherRequest:
    return SaveResearcherRequest(
        full_name=form_text(data, "full_name"),
        organization=form_text(data, "organization"),
    )
