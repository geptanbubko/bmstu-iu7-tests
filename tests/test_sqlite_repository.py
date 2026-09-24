import threading
from pathlib import Path
from typing import Iterator

import pytest

from wildlife_business.entities import Species
from wildlife_data import (
    DataValidationError,
    DuplicateEntityError,
    EntityNotFoundError,
    SqliteRepository,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "wildlife.db"


@pytest.fixture
def repo(db_path: Path) -> Iterator[SqliteRepository]:
    repository = SqliteRepository(db_path)
    yield repository
    repository.close()


def test_save_and_get_species_persisted(db_path: Path) -> None:
    with SqliteRepository(db_path) as repository:
        saved = repository.save_species(Species(None, "  Ursus arctos  ", "  Бурый медведь  "))
        assert saved.id is not None
        assert saved.scientific_name == "Ursus arctos"
        assert saved.common_name == "Бурый медведь"

    with SqliteRepository(db_path) as repository:
        fetched = repository.get_species(saved.id)
        assert fetched == saved
        assert repository.species_exists("Ursus arctos") is True


def test_update_species(repo: SqliteRepository) -> None:
    saved = repo.save_species(Species(None, "Canis lupus", "Волк"))

    updated = repo.update_species(Species(saved.id, "Canis lupus", "Серый волк"))

    assert updated.common_name == "Серый волк"
    assert repo.get_species(saved.id) == updated


def test_delete_species(repo: SqliteRepository) -> None:
    saved = repo.save_species(Species(None, "Felis silvestris", "Лесной кот"))
    assert saved.id is not None

    repo.delete_species(saved.id)

    assert repo.get_species(saved.id) is None
    assert repo.species_exists("Felis silvestris") is False


def test_save_species_rejects_empty_name(repo: SqliteRepository) -> None:
    with pytest.raises(DataValidationError, match="название"):
        repo.save_species(Species(None, "   ", "Волк"))


def test_save_species_duplicate(repo: SqliteRepository) -> None:
    repo.save_species(Species(None, "Lynx lynx", "Рысь"))

    with pytest.raises(DuplicateEntityError, match="уже существует"):
        repo.save_species(Species(None, "Lynx lynx", "Евразийская рысь"))


def test_delete_species_not_found(repo: SqliteRepository) -> None:
    with pytest.raises(EntityNotFoundError, match="не найден"):
        repo.delete_species(999)


def test_repository_usable_from_another_thread(db_path: Path) -> None:
    repo = SqliteRepository(db_path)
    repo.save_species(Species(None, "Alces alces", "Лось"))
    result: dict[str, list[Species]] = {}

    def worker() -> None:
        result["rows"] = repo.list_species()

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    repo.close()

    assert result["rows"][0].scientific_name == "Alces alces"
