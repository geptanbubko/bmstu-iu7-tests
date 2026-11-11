"""Ограничения БД (FOREIGN KEY) защищают хранилище, даже если бизнес-проверки пройдены."""
from datetime import date

import allure
import pytest

from wildlife_data.exceptions import IntegrityConstraintError

from tests.builders import an_observation
from tests.integration import seed

pytestmark = [
    allure.epic("Мониторинг популяции диких животных"),
    allure.feature("Integration: целостность данных"),
]

MISSING_ID = 999


@allure.story("Целостность хранилища")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("Ссылка на несуществующий вид и удаление вида с наблюдениями отклоняются БД")
def test_foreign_keys_keep_storage_consistent(observations, repository) -> None:
    # arrange
    orphan = (
        an_observation()
        .for_refs(MISSING_ID, seed.KIVACH_ID, seed.SMIRNOVA_ID)
        .on(date(2025, 9, 10))
        .with_count(1)
        .build()
    )
    period = (date(2025, 1, 1), date(2025, 12, 31))

    with allure.step("act + assert: наблюдение с несуществующим видом отклонено FOREIGN KEY"):
        with pytest.raises(IntegrityConstraintError, match="ссылочной"):
            observations.create_observation(orphan)

    with allure.step("act + assert: вид с наблюдениями нельзя удалить"):
        with pytest.raises(IntegrityConstraintError):
            repository.delete_species(seed.MOOSE_ID)

    with allure.step("assert: журнал, учёты и справочник не изменились"):
        assert len(observations.list_observations()) == seed.OBSERVATIONS_COUNT
        assert repository.find_population_records(MISSING_ID, *period) == []
        assert repository.get_species(seed.MOOSE_ID) is not None
        assert len(repository.find_population_records(seed.MOOSE_ID, *period)) == 5
