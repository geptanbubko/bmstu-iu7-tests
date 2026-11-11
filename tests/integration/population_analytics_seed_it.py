"""AnalyticsService + SqliteRepository: анализ по данным, заведённым скриптом 02_seed.sql."""
from datetime import date

import allure

from wildlife_business.analytics_service import INSUFFICIENT_DATA_MESSAGE, AnalyticsService
from wildlife_business.dto import PopulationAnalysisRequest

from tests.integration import seed

pytestmark = [
    allure.epic("Мониторинг популяции диких животных"),
    allure.feature("Integration: анализ динамики"),
]


@allure.story("Анализ динамики популяции")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("SQL-фильтр по виду, периоду и локации и порог тренда работают на реальных данных")
def test_population_analysis_over_seeded_storage(analytics, repository) -> None:
    # arrange
    moose_year = PopulationAnalysisRequest(seed.MOOSE_ID, *seed.YEAR_2025, seed.KIVACH_ID)
    moose_summer = PopulationAnalysisRequest(seed.MOOSE_ID, date(2025, 6, 1), date(2025, 7, 31))
    lynx_year = PopulationAnalysisRequest(seed.LYNX_ID, *seed.YEAR_2025)
    lenient = AnalyticsService(repository, min_records_for_trend=2)

    with allure.step("act: построить анализ лося за год, лета и рыси с двумя порогами"):
        moose = analytics.analyze_population(moose_year)
        summer = analytics.analyze_population(moose_summer)
        lynx_strict = analytics.analyze_population(lynx_year)
        lynx_lenient = lenient.analyze_population(lynx_year)

    with allure.step("assert: пять учётов лося по возрастанию дат — тренд построен"):
        assert moose.records_count == 5
        assert moose.has_trend is True
        assert moose.rows[0] == (date(2025, 4, 15), 11)
        assert moose.rows[-1] == (date(2025, 8, 15), 19)

    with allure.step("assert: BETWEEN по датам отсекает записи вне периода"):
        assert [d for d, _ in summer.rows] == [date(2025, 6, 15), date(2025, 7, 15)]

    with allure.step("assert: порог тренда из конфигурации меняет результат по рыси"):
        assert (lynx_strict.has_trend, lynx_strict.warning_message) == (False, INSUFFICIENT_DATA_MESSAGE)
        assert (lynx_lenient.has_trend, lynx_lenient.warning_message) == (True, None)
