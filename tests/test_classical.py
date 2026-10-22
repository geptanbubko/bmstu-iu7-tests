"""Классическая школа: реальные сервисы + SQLite :memory:, проверка состояния."""
from datetime import date

import allure
import pytest

from wildlife_business.analytics_service import AnalyticsService
from wildlife_business.catalog_service import CatalogService
from wildlife_business.dto import (
    CreateObservationRequest,
    PopulationAnalysisRequest,
    SaveLocationRequest,
    SaveResearcherRequest,
    SaveSpeciesRequest,
)
from wildlife_business.exceptions import DuplicateSpeciesError, NoDataError, ValidationError
from wildlife_business.observation_service import ObservationService

pytestmark = [
    allure.epic("Мониторинг популяции диких животных"),
    allure.feature("Классическая школа"),
    pytest.mark.classical,
]


@pytest.fixture
def catalog(repository):
    return CatalogService(repository)


@pytest.fixture
def observations(repository):
    return ObservationService(repository)


@pytest.fixture
def analytics(repository):
    return AnalyticsService(repository)


@allure.story("Сквозной сценарий учёта")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Справочник, наблюдения и тренд сохраняются согласованно")
def test_full_catalog_observation_and_trend_flow(catalog, observations, analytics) -> None:
    with allure.step("Добавить вид, локацию и исследователя"):
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
    with allure.step("Зафиксировать пять наблюдений с растущей численностью"):
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

    with allure.step("Прочитать наблюдения и построить тренд за год"):
        listed = observations.list_observations()
        result = analytics.analyze_population(
            PopulationAnalysisRequest(species.id, date(2026, 1, 1), date(2026, 12, 31), location.id)
        )

    with allure.step("Состояние справочника, журнала и тренда согласовано"):
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


@allure.story("Управление справочником видов")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Дубликат научного названия вида отклоняется")
def test_duplicate_species_is_rejected(catalog) -> None:
    with allure.step("Сохранить вид рыси"):
        catalog.add_species(SaveSpeciesRequest("Lynx lynx", "Рысь"))

    duplicate = SaveSpeciesRequest("Lynx lynx", "Евразийская рысь")
    with allure.step("Повторное добавление того же научного названия отклоняется"):
        with pytest.raises(DuplicateSpeciesError, match="уже зарегистрирован"):
            catalog.add_species(duplicate)

    with allure.step("В справочнике остаётся одна запись"):
        assert len(catalog.list_species()) == 1


@allure.story("Фиксация наблюдений")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Наблюдение в будущем не попадает в хранилище")
def test_future_observation_does_not_change_store(catalog, observations, analytics) -> None:
    with allure.step("Заполнить справочники"):
        species = catalog.add_species(SaveSpeciesRequest("Ursus arctos", "Бурый медведь"))
        location = catalog.add_location(SaveLocationRequest("Заповедник", "Карелия"))
        researcher = catalog.add_researcher(SaveResearcherRequest("Иванов И.И.", "ИУ7"))

    future = CreateObservationRequest(
        species.id, location.id, researcher.id, date(2099, 1, 1), 1
    )
    with allure.step("Дата в будущем отклоняется и журнал остаётся пустым"):
        with pytest.raises(ValidationError, match="будущем"):
            observations.create_observation(future)
        assert observations.list_observations() == []

    empty_period = PopulationAnalysisRequest(species.id, date(2026, 1, 1), date(2026, 12, 31))
    with allure.step("Анализ пустого периода не строится"):
        with pytest.raises(NoDataError):
            analytics.analyze_population(empty_period)


@allure.story("Фиксация наблюдений")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Наблюдение без вида, локации или исследователя не сохраняется")
def test_observation_without_reference_does_not_change_store(catalog, observations) -> None:
    with allure.step("Заполнить справочники"):
        species = catalog.add_species(SaveSpeciesRequest("Ursus arctos", "Бурый медведь"))
        location = catalog.add_location(SaveLocationRequest("Заповедник", "Карелия"))
        researcher = catalog.add_researcher(SaveResearcherRequest("Иванов И.И.", "ИУ7"))

    day = date(2026, 1, 10)
    rejected = (
        (
            CreateObservationRequest(0, location.id, researcher.id, day, 3, "без вида"),
            "вид животного",
        ),
        (
            CreateObservationRequest(species.id, 0, researcher.id, day, 3, "без локации"),
            "локацию",
        ),
        (
            CreateObservationRequest(species.id, location.id, 0, day, 3, "без исследователя"),
            "исследователя",
        ),
    )

    with allure.step("Каждая битая ссылка отклоняется"):
        for request, message in rejected:
            with pytest.raises(ValidationError, match=message):
                observations.create_observation(request)

    with allure.step("Журнал наблюдений не изменился"):
        assert observations.list_observations() == []


@allure.story("Анализ динамики популяции")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Анализ периода без учётов завершается ошибкой")
def test_analysis_without_records_fails(catalog, analytics) -> None:
    with allure.step("Заполнить справочник вида без наблюдений"):
        species = catalog.add_species(SaveSpeciesRequest("Ursus arctos", "Бурый медведь"))

    request = PopulationAnalysisRequest(species.id, date(2026, 1, 1), date(2026, 1, 31))
    with allure.step("Анализ января без записей отклоняется"):
        with pytest.raises(NoDataError, match="отсутствуют"):
            analytics.analyze_population(request)


@allure.story("Управление справочником видов")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Пустое научное название вида отклоняется")
def test_empty_species_name_is_rejected(catalog) -> None:
    request = SaveSpeciesRequest("   ", "Волк")
    with allure.step("Вид с пустым научным названием не сохраняется"):
        with pytest.raises(ValidationError, match="обязательные"):
            catalog.add_species(request)
        assert catalog.list_species() == []
