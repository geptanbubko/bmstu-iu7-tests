"""Откат хранилища: после изменений и сбоя данные возвращаются к состоянию до прогона."""
import allure
import pytest

from db import dbctl
from wildlife_business.dto import SaveLocationRequest, SaveSpeciesRequest

from tests.integration import seed

pytestmark = [
    allure.epic("Мониторинг популяции диких животных"),
    allure.feature("Integration: развёртывание хранилища"),
]


@allure.story("Откат хранилища")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("Изменённое хранилище распознаётся и откатывается скриптами к эталону")
def test_rollback_restores_reference_state(catalog, repository, storage) -> None:
    # arrange
    catalog.add_species(SaveSpeciesRequest("Vulpes vulpes", "Лисица"))
    catalog.add_location(SaveLocationRequest("Валаам", "Карелия"))
    repository.close()

    with allure.step("act + assert: verify видит отличие от эталона"):
        with pytest.raises(dbctl.StorageIntegrityError, match="отличается"):
            dbctl.verify(storage.path, storage.reference)

    with allure.step("act: выполнить 90_rollback.sql + 02_seed.sql"):
        dbctl.rollback(storage.path)
        restored = dbctl.verify(storage.path, storage.reference)

    with allure.step("assert: состояние и счётчики id совпадают с эталоном"):
        assert restored == storage.reference
        assert restored.row_counts["species"] == seed.SPECIES_COUNT
        assert catalog.add_species(SaveSpeciesRequest("Vulpes vulpes", "Лисица")).id == seed.SPECIES_COUNT + 1
