"""Сценарий: добавление наблюдения (BPMN 10.1)."""
from datetime import date

from wildlife_business.exceptions import ValidationError
from wildlife_business.dto import CreateObservationRequest
from wildlife_business.entities import Observation
from wildlife_business.repository import IRepository


class ObservationService:
    def __init__(self, repo: IRepository) -> None:
        self._repo = repo

    def create_observation(self, request: CreateObservationRequest) -> Observation:
        self._validate(request)
        saved = self._repo.add_observation(
            Observation(
                id=None,
                observation_date=request.observation_date,
                individuals_count=request.individuals_count,
                species_id=request.species_id,
                location_id=request.location_id,
                researcher_id=request.researcher_id,
                notes=request.notes,
            )
        )
        self._repo.upsert_population_record(
            species_id=saved.species_id,
            location_id=saved.location_id,
            researcher_id=saved.researcher_id,
            record_date=saved.observation_date,
            population_size=saved.individuals_count,
        )
        return saved

    def list_observations(self) -> list[Observation]:
        return self._repo.list_observations()

    def _validate(self, request: CreateObservationRequest) -> None:
        if request.species_id <= 0:
            raise ValidationError("Укажите вид животного")
        if request.location_id <= 0:
            raise ValidationError("Укажите локацию")
        if request.researcher_id <= 0:
            raise ValidationError("Укажите исследователя")
        if request.individuals_count < 0:
            raise ValidationError("Количество особей не может быть отрицательным")
        if request.observation_date > date.today():
            raise ValidationError("Дата наблюдения не может быть в будущем")
