"""Лондонская школа: изоляция через моки, проверка взаимодействий."""
from datetime import date
from unittest.mock import Mock

import allure
import pytest

from wildlife_business.analytics_service import AnalyticsService
from wildlife_business.catalog_service import CatalogService
from wildlife_business.dto import (
    CreateObservationRequest,
    PopulationAnalysisRequest,
    SaveSpeciesRequest,
)
from wildlife_business.entities import Observation, PopulationRecord, Species
from wildlife_business.exceptions import NotFoundError, ValidationError
from wildlife_business.observation_service import ObservationService
from wildlife_data.sqlite_repository import SqliteRepository

pytestmark = [
    allure.epic("Мониторинг популяции диких животных"),
    allure.feature("Лондонская школа"),
    pytest.mark.london,
]


@allure.story("Фиксация наблюдений")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Создание наблюдения пишет учёт и запись численности")
def test_create_observation_notifies_repository_twice() -> None:
    repo = Mock()
    saved = Observation(10, date(2026, 3, 1), 7, 1, 2, 3, "у реки")
    repo.add_observation.return_value = saved
    service = ObservationService(repo)

    with allure.step("Создать наблюдение через сервис"):
        result = service.create_observation(
            CreateObservationRequest(1, 2, 3, date(2026, 3, 1), 7, "у реки")
        )

    with allure.step("Репозиторий получил наблюдение и обновление численности"):
        assert result is saved
        repo.add_observation.assert_called_once()
        payload = repo.add_observation.call_args[0][0]
        assert payload.id is None
        assert payload.individuals_count == 7
        repo.upsert_population_record.assert_called_once_with(
            species_id=1,
            location_id=2,
            researcher_id=3,
            record_date=date(2026, 3, 1),
            population_size=7,
        )


@allure.story("Фиксация наблюдений")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Отрицательная численность не вызывает репозиторий")
def test_invalid_observation_does_not_touch_repository() -> None:
    repo = Mock()
    service = ObservationService(repo)

    request = CreateObservationRequest(1, 2, 3, date(2026, 3, 1), -4)
    with allure.step("Сервис отклоняет отрицательную численность до записи"):
        with pytest.raises(ValidationError, match="отрицательным"):
            service.create_observation(request)
        repo.add_observation.assert_not_called()
        repo.upsert_population_record.assert_not_called()


@allure.story("Управление справочником видов")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Новый вид проверяется на дубликат и сохраняется нормализованным")
def test_add_species_checks_catalog_before_save() -> None:
    repo = Mock()
    repo.species_exists.return_value = False
    repo.save_species.return_value = Species(1, "Felis silvestris", "Лесной кот")
    service = CatalogService(repo)

    with allure.step("Добавить вид с лишними пробелами в названии"):
        service.add_species(SaveSpeciesRequest("  Felis silvestris  ", "  Лесной кот  "))

    with allure.step("Сначала проверка каталога, затем сохранение без пробелов"):
        repo.species_exists.assert_called_once_with("Felis silvestris")
        saved = repo.save_species.call_args[0][0]
        assert saved.id is None
        assert saved.scientific_name == "Felis silvestris"
        assert saved.common_name == "Лесной кот"


@allure.story("Управление справочником видов")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Обновление отсутствующего вида не доходит до записи")
def test_update_species_stops_when_missing() -> None:
    repo = Mock()
    repo.get_species.return_value = None
    service = CatalogService(repo)

    request = SaveSpeciesRequest("Canis lupus", "Волк")
    with allure.step("Обновление неизвестного id останавливается на чтении"):
        with pytest.raises(NotFoundError, match="не найден"):
            service.update_species(9, request)
        repo.get_species.assert_called_once_with(9)
        repo.update_species.assert_not_called()
        repo.species_exists.assert_not_called()


@allure.story("Анализ динамики популяции")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Анализ передаёт фильтр вида, периода и локации в репозиторий")
def test_analyze_population_forwards_filter_to_repository() -> None:
    repo = Mock()
    repo.find_population_records.return_value = [
        PopulationRecord(date(2026, 4, 1), 12),
        PopulationRecord(date(2026, 5, 1), 15),
        PopulationRecord(date(2026, 6, 1), 18),
        PopulationRecord(date(2026, 7, 1), 20),
        PopulationRecord(date(2026, 8, 1), 22),
    ]
    service = AnalyticsService(repo)

    with allure.step("Построить анализ по виду, году и локации"):
        result = service.analyze_population(
            PopulationAnalysisRequest(4, date(2026, 1, 1), date(2026, 12, 31), location_id=8)
        )

    with allure.step("В репозиторий ушёл тот же фильтр, тренд построен"):
        repo.find_population_records.assert_called_once_with(
            4, date(2026, 1, 1), date(2026, 12, 31), 8
        )
        assert result.has_trend is True
        assert result.records_count == 5


@allure.story("Изоляция доступа к данным")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("SqliteRepository открывает подменённое соединение, а не реальную БД")
def test_sqlite_repository_uses_substituted_connection(
    substituted_connection, connect_spy
) -> None:
    with allure.step("Открыть репозиторий по файловому пути"):
        repo = SqliteRepository("/production/wildlife.db")

    with allure.step("connect вызван с этим путём, курсор и схема — на подмене"):
        assert repo.list_species() == []
        connect_spy.assert_called_with("/production/wildlife.db")
        assert substituted_connection._opened_with == "/production/wildlife.db"
        substituted_connection.executescript.assert_called()
        substituted_connection.execute.assert_called()
        repo.close()
        substituted_connection.close.assert_called()
