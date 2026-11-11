"""ObservationService + SqliteRepository: наблюдение пишет журнал и обновляет учёт численности."""
from datetime import date

import allure

from wildlife_business.dto import PopulationAnalysisRequest

from tests.builders import an_observation
from tests.integration import seed

pytestmark = [
    allure.epic("Мониторинг популяции диких животных"),
    allure.feature("Integration: фиксация наблюдений"),
]


@allure.story("Фиксация наблюдений")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Два наблюдения за день дают две записи журнала и один учёт с последним значением")
def test_observation_upserts_population_record(observations, analytics) -> None:
    # arrange
    day = date(2025, 9, 1)
    wolverine = an_observation().for_refs(seed.WOLVERINE_ID, seed.LAPLAND_ID, seed.ORLOV_ID).on(day)
    morning = wolverine.with_count(4).with_notes("утро").build()
    evening = wolverine.with_count(6).with_notes("вечер").build()
    period = PopulationAnalysisRequest(seed.WOLVERINE_ID, *seed.YEAR_2025, seed.LAPLAND_ID)

    with allure.step("act: зафиксировать два наблюдения росомахи за один день"):
        first = observations.create_observation(morning)
        second = observations.create_observation(evening)
        journal = observations.list_observations()
        result = analytics.analyze_population(period)

    with allure.step("assert: журнал дополнен двумя строками с новыми id"):
        assert len(journal) == seed.OBSERVATIONS_COUNT + 2
        assert (first.id, second.id) == (seed.OBSERVATIONS_COUNT + 1, seed.OBSERVATIONS_COUNT + 2)
        assert [o.notes for o in journal if o.species_id == seed.WOLVERINE_ID] == ["утро", "вечер"]

    with allure.step("assert: учёт численности за день один и содержит последнее значение"):
        assert result.records_count == 1
        assert result.rows == [(day, 6)]
        assert result.has_trend is False
