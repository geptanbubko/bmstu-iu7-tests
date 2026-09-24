from datetime import date
from unittest.mock import Mock

import pytest

from wildlife_business.exceptions import ValidationError
from wildlife_business.observation_service import ObservationService
from wildlife_business.dto import CreateObservationRequest
from wildlife_business.entities import Observation


@pytest.fixture
def repo() -> Mock:
    return Mock()


@pytest.fixture
def service(repo: Mock) -> ObservationService:
    return ObservationService(repo)


def test_create_observation_success(service: ObservationService, repo: Mock) -> None:
    request = CreateObservationRequest(
        species_id=1,
        location_id=2,
        researcher_id=3,
        observation_date=date(2025, 1, 10),
        individuals_count=4,
        notes="группа у водопоя",
    )
    saved = Observation(10, date(2025, 1, 10), 4, 1, 2, 3, "группа у водопоя")
    repo.add_observation.return_value = saved

    result = service.create_observation(request)

    assert result == saved
    repo.add_observation.assert_called_once()
    repo.upsert_population_record.assert_called_once_with(
        species_id=1,
        location_id=2,
        researcher_id=3,
        record_date=date(2025, 1, 10),
        population_size=4,
    )
    arg = repo.add_observation.call_args[0][0]
    assert arg.species_id == 1
    assert arg.individuals_count == 4


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("species_id", 0, "Укажите вид животного"),
        ("location_id", -1, "Укажите локацию"),
        ("researcher_id", 0, "Укажите исследователя"),
    ],
)
def test_create_observation_invalid_reference(
    service: ObservationService,
    repo: Mock,
    field: str,
    value: int,
    message: str,
) -> None:
    data = {
        "species_id": 1,
        "location_id": 2,
        "researcher_id": 3,
        "observation_date": date(2025, 1, 1),
        "individuals_count": 1,
    }
    data[field] = value
    request = CreateObservationRequest(**data)

    with pytest.raises(ValidationError, match=message):
        service.create_observation(request)

    repo.add_observation.assert_not_called()


def test_create_observation_negative_count(
    service: ObservationService, repo: Mock
) -> None:
    request = CreateObservationRequest(1, 2, 3, date(2025, 1, 1), -1)

    with pytest.raises(ValidationError, match="отрицательным"):
        service.create_observation(request)

    repo.add_observation.assert_not_called()


def test_create_observation_future_date(
    service: ObservationService, repo: Mock
) -> None:
    request = CreateObservationRequest(1, 2, 3, date(2099, 1, 1), 1)

    with pytest.raises(ValidationError, match="будущем"):
        service.create_observation(request)

    repo.add_observation.assert_not_called()
