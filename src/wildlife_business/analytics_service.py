"""Сценарий: анализ динамики популяции (BPMN 10.2)."""
from wildlife_business.dto import PopulationAnalysisRequest, PopulationAnalysisResult
from wildlife_business.exceptions import NoDataError, ValidationError
from wildlife_business.repository import IRepository

DEFAULT_MIN_RECORDS_FOR_TREND = 5
MIN_RECORDS_FOR_TREND = DEFAULT_MIN_RECORDS_FOR_TREND
INSUFFICIENT_DATA_MESSAGE = "Недостаточно данных для тренда"


class AnalyticsService:
    def __init__(
        self,
        repo: IRepository,
        min_records_for_trend: int = DEFAULT_MIN_RECORDS_FOR_TREND,
    ) -> None:
        if min_records_for_trend <= 0:
            raise ValidationError("Порог тренда должен быть положительным")
        self._repo = repo
        self._min_records_for_trend = min_records_for_trend

    def analyze_population(
        self, request: PopulationAnalysisRequest
    ) -> PopulationAnalysisResult:
        if request.species_id <= 0:
            raise ValidationError("Укажите вид животного")
        if request.date_from > request.date_to:
            raise ValidationError("Дата начала периода не может быть позже даты окончания")

        records = self._repo.find_population_records(
            request.species_id,
            request.date_from,
            request.date_to,
            request.location_id,
        )
        if not records:
            raise NoDataError("Данные за период отсутствуют")

        rows = [(r.record_date, r.population_size) for r in records]
        count = len(records)
        has_trend = count >= self._min_records_for_trend
        warning = None if has_trend else INSUFFICIENT_DATA_MESSAGE

        return PopulationAnalysisResult(
            records_count=count,
            has_trend=has_trend,
            rows=rows,
            warning_message=warning,
        )
