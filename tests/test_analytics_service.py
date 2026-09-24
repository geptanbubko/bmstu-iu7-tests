from datetime import date
from unittest.mock import Mock

import pytest

from wildlife_business.analytics_service import AnalyticsService, MIN_RECORDS_FOR_TREND
from wildlife_business.exceptions import NoDataError, ValidationError
from wildlife_business.dto import PopulationAnalysisRequest
from wildlife_business.entities import PopulationRecord


@pytest.fixture
def repo() -> Mock:
    return Mock()


@pytest.fixture
def service(repo: Mock) -> AnalyticsService:
    return AnalyticsService(repo)


def _records(count: int) -> list[PopulationRecord]:
    return [
        PopulationRecord(date(2025, 1, i + 1), 10 + i)
        for i in range(count)
    ]


def test_analyze_population_with_trend(service: AnalyticsService, repo: Mock) -> None:
    repo.find_population_records.return_value = _records(MIN_RECORDS_FOR_TREND)
    request = PopulationAnalysisRequest(1, date(2025, 1, 1), date(2025, 12, 31))

    result = service.analyze_population(request)

    assert result.records_count == MIN_RECORDS_FOR_TREND
    assert result.has_trend is True
    assert result.warning_message is None
    assert len(result.rows) == MIN_RECORDS_FOR_TREND
    repo.find_population_records.assert_called_once_with(1, date(2025, 1, 1), date(2025, 12, 31), None)


def test_analyze_population_insufficient_data(
    service: AnalyticsService, repo: Mock
) -> None:
    repo.find_population_records.return_value = _records(3)
    request = PopulationAnalysisRequest(1, date(2025, 1, 1), date(2025, 6, 1))

    result = service.analyze_population(request)

    assert result.records_count == 3
    assert result.has_trend is False
    assert result.warning_message == "Недостаточно данных для тренда"


def test_analyze_population_no_data(service: AnalyticsService, repo: Mock) -> None:
    repo.find_population_records.return_value = []
    request = PopulationAnalysisRequest(2, date(2024, 1, 1), date(2024, 2, 1))

    with pytest.raises(NoDataError, match="отсутствуют"):
        service.analyze_population(request)


def test_analyze_population_invalid_species(
    service: AnalyticsService, repo: Mock
) -> None:
    request = PopulationAnalysisRequest(0, date(2025, 1, 1), date(2025, 2, 1))

    with pytest.raises(ValidationError, match="вид"):
        service.analyze_population(request)

    repo.find_population_records.assert_not_called()


def test_analyze_population_invalid_period(
    service: AnalyticsService, repo: Mock
) -> None:
    request = PopulationAnalysisRequest(1, date(2025, 6, 1), date(2025, 1, 1))

    with pytest.raises(ValidationError, match="периода"):
        service.analyze_population(request)

    repo.find_population_records.assert_not_called()


def test_analyze_population_custom_threshold(repo: Mock) -> None:
    repo.find_population_records.return_value = _records(3)
    service = AnalyticsService(repo, min_records_for_trend=3)
    request = PopulationAnalysisRequest(1, date(2025, 1, 1), date(2025, 12, 31))

    result = service.analyze_population(request)

    assert result.has_trend is True
    assert result.warning_message is None


def test_analyze_population_with_location_filter(
    service: AnalyticsService, repo: Mock
) -> None:
    repo.find_population_records.return_value = _records(5)
    request = PopulationAnalysisRequest(
        1, date(2025, 1, 1), date(2025, 12, 31), location_id=7
    )

    service.analyze_population(request)

    repo.find_population_records.assert_called_once_with(
        1, date(2025, 1, 1), date(2025, 12, 31), 7
    )

