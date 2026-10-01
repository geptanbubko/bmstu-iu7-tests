"""Классическая школа: реальные сервисы + fake-хранилище, проверка состояния."""
from datetime import date

import pytest

from wildlife_business.dto import (
    CreateObservationRequest,
    PopulationAnalysisRequest,
    SaveLocationRequest,
    SaveResearcherRequest,
    SaveSpeciesRequest,
)
from wildlife_business.exceptions import DuplicateSpeciesError, NoDataError, ValidationError


def _seed_catalog(catalog) -> None:
    catalog.add_species(SaveSpeciesRequest("Ursus arctos", "Бурый медведь"))
    catalog.add_location(SaveLocationRequest("Заповедник", "Карелия"))
    catalog.add_researcher(SaveResearcherRequest("Иванов И.И.", "ИУ7"))


@pytest.mark.classical
def test_full_catalog_observation_and_trend_flow(services) -> None:
    catalog = services["catalog"]
    observations = services["observations"]
    analytics = services["analytics"]

    species = catalog.add_species(SaveSpeciesRequest("  Canis lupus  ", "  Волк  "))
    updated = catalog.update_species(species.id, SaveSpeciesRequest("Canis lupus", "Серый волк"))
    location = catalog.add_location(SaveLocationRequest("Лапландия", "Мурманская область"))
    researcher = catalog.add_researcher(SaveResearcherRequest("Петров П.П.", "ИУ7"))

    counts = (2, 4, 5, 8, 10)
    days = (
        date(2026, 1, 10),
        date(2026, 2, 10),
        date(2026, 3, 10),
        date(2026, 4, 10),
        date(2026, 5, 10),
    )
    for day, count in zip(days, counts):
        observations.create_observation(
            CreateObservationRequest(
                species_id=species.id,
                location_id=location.id,
                researcher_id=researcher.id,
                observation_date=day,
                individuals_count=count,
                notes="учёт",
            )
        )

    listed = observations.list_observations()
    result = analytics.analyze_population(
        PopulationAnalysisRequest(species.id, date(2026, 1, 1), date(2026, 12, 31), location.id)
    )

    assert updated.common_name == "Серый волк"
    assert [row.common_name for row in catalog.list_species()] == ["Серый волк"]
    assert catalog.list_locations()[0].name == "Лапландия"
    assert catalog.list_researchers()[0].full_name == "Петров П.П."
    assert len(listed) == 5
    assert listed[0].individuals_count == 2
    assert listed[-1].observation_date == date(2026, 5, 10)
    assert result.records_count == 5
    assert result.has_trend is True
    assert result.warning_message is None
    assert result.rows[-1] == (date(2026, 5, 10), 10)


@pytest.mark.classical
def test_duplicate_species_is_rejected(services) -> None:
    catalog = services["catalog"]
    catalog.add_species(SaveSpeciesRequest("Lynx lynx", "Рысь"))

    with pytest.raises(DuplicateSpeciesError, match="уже зарегистрирован"):
        catalog.add_species(SaveSpeciesRequest("Lynx lynx", "Евразийская рысь"))

    assert len(catalog.list_species()) == 1


@pytest.mark.classical
def test_future_observation_does_not_change_store(services) -> None:
    _seed_catalog(services["catalog"])

    with pytest.raises(ValidationError, match="будущем"):
        services["observations"].create_observation(
            CreateObservationRequest(1, 2, 3, date(2099, 1, 1), 1)
        )

    assert services["observations"].list_observations() == []
    with pytest.raises(NoDataError):
        services["analytics"].analyze_population(
            PopulationAnalysisRequest(1, date(2026, 1, 1), date(2026, 12, 31))
        )


@pytest.mark.classical
def test_analysis_without_records_fails(services) -> None:
    _seed_catalog(services["catalog"])

    with pytest.raises(NoDataError, match="отсутствуют"):
        services["analytics"].analyze_population(
            PopulationAnalysisRequest(1, date(2026, 1, 1), date(2026, 1, 31))
        )


@pytest.mark.classical
def test_empty_species_name_is_rejected(services) -> None:
    with pytest.raises(ValidationError, match="обязательные"):
        services["catalog"].add_species(SaveSpeciesRequest("   ", "Волк"))

    assert services["catalog"].list_species() == []
