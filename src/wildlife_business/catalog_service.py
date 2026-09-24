"""Сценарий: управление справочниками (BPMN 10.3, use case видов и локаций)."""
from wildlife_business.exceptions import DuplicateSpeciesError, NotFoundError, ValidationError
from wildlife_business.dto import SaveLocationRequest, SaveResearcherRequest, SaveSpeciesRequest
from wildlife_business.entities import Location, Researcher, Species
from wildlife_business.repository import IRepository


class CatalogService:
    def __init__(self, repo: IRepository) -> None:
        self._repo = repo

    def add_species(self, request: SaveSpeciesRequest) -> Species:
        scientific, common = self._validated_species_names(request)
        if self._repo.species_exists(scientific):
            raise DuplicateSpeciesError("Такой вид уже зарегистрирован")
        return self._repo.save_species(Species(None, scientific, common))

    def update_species(self, species_id: int, request: SaveSpeciesRequest) -> Species:
        if species_id <= 0:
            raise ValidationError("Укажите вид животного")
        existing = self._repo.get_species(species_id)
        if existing is None:
            raise NotFoundError("Вид не найден")
        scientific, common = self._validated_species_names(request)
        if scientific != existing.scientific_name and self._repo.species_exists(scientific):
            raise DuplicateSpeciesError("Такой вид уже зарегистрирован")
        return self._repo.update_species(Species(species_id, scientific, common))

    def list_species(self) -> list[Species]:
        return self._repo.list_species()

    def add_location(self, request: SaveLocationRequest) -> Location:
        name = request.name.strip()
        if not name:
            raise ValidationError("Заполните название локации")
        region = request.region.strip() or None
        return self._repo.save_location(Location(None, name, region))

    def list_locations(self) -> list[Location]:
        return self._repo.list_locations()

    def add_researcher(self, request: SaveResearcherRequest) -> Researcher:
        full_name = request.full_name.strip()
        if not full_name:
            raise ValidationError("Заполните ФИО исследователя")
        organization = request.organization.strip() or None
        return self._repo.save_researcher(Researcher(None, full_name, organization))

    def list_researchers(self) -> list[Researcher]:
        return self._repo.list_researchers()

    @staticmethod
    def _validated_species_names(request: SaveSpeciesRequest) -> tuple[str, str]:
        scientific = request.scientific_name.strip()
        common = request.common_name.strip()
        if not scientific or not common:
            raise ValidationError("Заполните все обязательные поля")
        return scientific, common
