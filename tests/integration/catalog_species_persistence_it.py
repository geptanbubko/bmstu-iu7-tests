"""CatalogService + SqliteRepository: вид сохраняется в файл и переживает переподключение."""
import allure
import pytest

from wildlife_business.dto import SaveSpeciesRequest
from wildlife_business.entities import Species
from wildlife_business.exceptions import DuplicateSpeciesError
from wildlife_data.exceptions import DuplicateEntityError
from wildlife_data.sqlite_repository import SqliteRepository

from tests.integration import seed

pytestmark = [
    allure.epic("Мониторинг популяции диких животных"),
    allure.feature("Integration: справочник видов"),
]


@allure.story("Управление справочником видов")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Добавленный и изменённый вид хранится в БД, дубликаты отклоняются на обоих слоях")
def test_species_catalog_persists_between_connections(catalog, repository, storage) -> None:
    # arrange
    bear = SaveSpeciesRequest("  Ursus arctos ", " Медведь ")
    renamed = SaveSpeciesRequest("Ursus arctos", "Бурый медведь")
    seed_duplicate = SaveSpeciesRequest("Lynx lynx", "Евразийская рысь")

    with allure.step("act: добавить вид и переименовать его через бизнес-логику"):
        created = catalog.add_species(bear)
        updated = catalog.update_species(created.id, renamed)

    with allure.step("act: открыть новое соединение к тому же файлу хранилища"):
        with SqliteRepository(storage.path) as reopened:
            persisted = reopened.get_species(created.id)
            persisted_all = reopened.list_species()

    with allure.step("assert: данные пережили переподключение и нормализованы"):
        assert updated == Species(created.id, "Ursus arctos", "Бурый медведь")
        assert persisted == updated
        assert len(persisted_all) == seed.SPECIES_COUNT + 1
        assert created.id == seed.SPECIES_COUNT + 1

    with allure.step("assert: дубликат вида из тестовых данных отклоняет бизнес-логика"):
        with pytest.raises(DuplicateSpeciesError):
            catalog.add_species(seed_duplicate)

    with allure.step("assert: в обход бизнес-логики дубликат отклоняет UNIQUE в БД"):
        with pytest.raises(DuplicateEntityError):
            repository.save_species(Species(None, "Lynx lynx", "Рысь-дубликат"))
        assert len(catalog.list_species()) == seed.SPECIES_COUNT + 1
