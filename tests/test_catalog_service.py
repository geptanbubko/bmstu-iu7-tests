from unittest.mock import Mock

import pytest

from wildlife_business.catalog_service import CatalogService
from wildlife_business.exceptions import DuplicateSpeciesError, NotFoundError, ValidationError
from wildlife_business.dto import SaveSpeciesRequest
from wildlife_business.entities import Species


@pytest.fixture
def repo() -> Mock:
    return Mock()


@pytest.fixture
def service(repo: Mock) -> CatalogService:
    return CatalogService(repo)


def test_add_species_success(service: CatalogService, repo: Mock) -> None:
    repo.species_exists.return_value = False
    repo.save_species.return_value = Species(1, "Ursus arctos", "Бурый медведь")
    request = SaveSpeciesRequest("  Ursus arctos  ", "  Бурый медведь  ")

    result = service.add_species(request)

    assert result.id == 1
    repo.species_exists.assert_called_once_with("Ursus arctos")
    saved = repo.save_species.call_args[0][0]
    assert saved.scientific_name == "Ursus arctos"
    assert saved.common_name == "Бурый медведь"


@pytest.mark.parametrize(
    "scientific,common",
    [
        ("", "Волк"),
        ("   ", "Волк"),
        ("Canis lupus", ""),
        ("Canis lupus", "   "),
    ],
)
def test_add_species_empty_fields(
    service: CatalogService,
    repo: Mock,
    scientific: str,
    common: str,
) -> None:
    with pytest.raises(ValidationError, match="обязательные"):
        service.add_species(SaveSpeciesRequest(scientific, common))

    repo.species_exists.assert_not_called()
    repo.save_species.assert_not_called()


def test_add_species_duplicate(service: CatalogService, repo: Mock) -> None:
    repo.species_exists.return_value = True

    with pytest.raises(DuplicateSpeciesError, match="уже зарегистрирован"):
        service.add_species(SaveSpeciesRequest("Felis catus", "Кошка"))

    repo.save_species.assert_not_called()


def test_update_species_success(service: CatalogService, repo: Mock) -> None:
    repo.get_species.return_value = Species(1, "Canis lupus", "Волк")
    repo.update_species.return_value = Species(1, "Canis lupus", "Серый волк")
    request = SaveSpeciesRequest("Canis lupus", "Серый волк")

    result = service.update_species(1, request)

    assert result.common_name == "Серый волк"
    repo.update_species.assert_called_once()


def test_update_species_not_found(service: CatalogService, repo: Mock) -> None:
    repo.get_species.return_value = None

    with pytest.raises(NotFoundError, match="не найден"):
        service.update_species(9, SaveSpeciesRequest("Canis lupus", "Волк"))

    repo.update_species.assert_not_called()
