"""HTTP JSON API (/api/v1) поверх тех же сервисов, что и GUI.

Используется E2E-тестами, Postman-коллекцией и curl-сценарием. Доступ — по токену
сессии (Authorization: Bearer ...), роли совпадают с ролями GUI.
"""
from __future__ import annotations

import logging
from datetime import date
from functools import wraps
from typing import Any, Callable

from flask import Blueprint, Response, g, jsonify, request

from wildlife_business.analytics_service import AnalyticsService
from wildlife_business.catalog_service import CatalogService
from wildlife_business.dto import (
    CreateObservationRequest,
    PopulationAnalysisRequest,
    SaveLocationRequest,
    SaveResearcherRequest,
    SaveSpeciesRequest,
)
from wildlife_business.exceptions import (
    BusinessError,
    DuplicateSpeciesError,
    NoDataError,
    NotFoundError,
)
from wildlife_data.exceptions import (
    DataAccessError,
    DataValidationError,
    DuplicateEntityError,
    EntityNotFoundError,
)
from wildlife_business.observation_service import ObservationService
from wildlife_gui.sessions import SessionRegistry
from wildlife_gui.viewmodels import ROLE_ADMIN, ROLE_LABELS, ROLE_RESEARCHER

logger = logging.getLogger("wildlife.api")

ALL_ROLES = (ROLE_ADMIN, ROLE_RESEARCHER)


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _error_status(exc: Exception) -> int:
    if isinstance(exc, (NotFoundError, EntityNotFoundError, NoDataError)):
        return 404
    if isinstance(exc, (DuplicateSpeciesError, DuplicateEntityError)):
        return 409
    if isinstance(exc, DataValidationError):
        return 400
    if isinstance(exc, BusinessError):
        return 400
    return 409  # прочие DataAccessError — нарушение ограничений хранилища


def _payload() -> dict[str, Any]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError(400, "Ожидается JSON-объект")
    return body


def _required(body: dict[str, Any], key: str) -> Any:
    if key not in body or body[key] is None:
        raise ApiError(400, f"Не задано поле {key}")
    return body[key]


def _as_int(value: Any, key: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(400, f"Поле {key} должно быть целым числом") from exc


def _as_date(value: Any, key: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ApiError(400, f"Поле {key} должно быть датой YYYY-MM-DD") from exc


def _species_json(item) -> dict[str, Any]:
    return {"id": item.id, "scientific_name": item.scientific_name, "common_name": item.common_name}


def _location_json(item) -> dict[str, Any]:
    return {"id": item.id, "name": item.name, "region": item.region}


def _researcher_json(item) -> dict[str, Any]:
    return {"id": item.id, "full_name": item.full_name, "organization": item.organization}


def _observation_json(item) -> dict[str, Any]:
    return {
        "id": item.id,
        "observation_date": item.observation_date.isoformat(),
        "individuals_count": item.individuals_count,
        "species_id": item.species_id,
        "location_id": item.location_id,
        "researcher_id": item.researcher_id,
        "notes": item.notes,
    }


def create_api_blueprint(
    observations: ObservationService,
    catalog: CatalogService,
    analytics: AnalyticsService,
    sessions: SessionRegistry,
) -> Blueprint:
    api = Blueprint("api", __name__, url_prefix="/api/v1")

    def require(*roles: str) -> Callable:
        def decorator(view: Callable) -> Callable:
            @wraps(view)
            def wrapped(*args, **kwargs):
                header = request.headers.get("Authorization", "")
                token = header[7:].strip() if header.startswith("Bearer ") else ""
                current = sessions.get(token) if token else None
                if current is None:
                    raise ApiError(401, "Требуется активная сессия")
                if current.role not in roles:
                    raise ApiError(403, "Недостаточно прав для роли")
                g.api_session = current
                return view(*args, **kwargs)

            return wrapped

        return decorator

    @api.errorhandler(ApiError)
    def api_error(exc: ApiError):
        return jsonify(error=exc.message), exc.status

    @api.errorhandler(BusinessError)
    @api.errorhandler(DataAccessError)
    def domain_error(exc: Exception):
        logger.warning("API: %s", exc)
        return jsonify(error=str(exc)), _error_status(exc)

    # --- служебное ---
    @api.get("/health")
    def health():
        return jsonify(status="ok", active_sessions=sessions.count())

    @api.post("/session")
    def open_session():
        role = str(_required(_payload(), "role")).strip()
        if role not in ROLE_LABELS:
            raise ApiError(400, "Неизвестная роль")
        created = sessions.open(role)
        logger.info("API: открыта сессия роли %s", role)
        return jsonify(token=created.token, role=created.role), 201

    @api.delete("/session")
    @require(*ALL_ROLES)
    def close_session():
        sessions.close(g.api_session.token)
        return Response(status=204)

    @api.delete("/sessions")
    @require(ROLE_ADMIN)
    def close_all_sessions():
        closed = sessions.close_all()
        logger.info("API: завершены все сессии (%s)", closed)
        return jsonify(closed=closed)

    # --- справочники (администратор) ---
    @api.get("/species")
    @require(*ALL_ROLES)
    def list_species():
        return jsonify([_species_json(s) for s in catalog.list_species()])

    @api.post("/species")
    @require(ROLE_ADMIN)
    def add_species():
        body = _payload()
        created = catalog.add_species(
            SaveSpeciesRequest(
                str(_required(body, "scientific_name")), str(_required(body, "common_name"))
            )
        )
        return jsonify(_species_json(created)), 201

    @api.put("/species/<int:species_id>")
    @require(ROLE_ADMIN)
    def update_species(species_id: int):
        body = _payload()
        updated = catalog.update_species(
            species_id,
            SaveSpeciesRequest(
                str(_required(body, "scientific_name")), str(_required(body, "common_name"))
            ),
        )
        return jsonify(_species_json(updated))

    @api.get("/locations")
    @require(*ALL_ROLES)
    def list_locations():
        return jsonify([_location_json(x) for x in catalog.list_locations()])

    @api.post("/locations")
    @require(ROLE_ADMIN)
    def add_location():
        body = _payload()
        created = catalog.add_location(
            SaveLocationRequest(str(_required(body, "name")), str(body.get("region") or ""))
        )
        return jsonify(_location_json(created)), 201

    @api.get("/researchers")
    @require(*ALL_ROLES)
    def list_researchers():
        return jsonify([_researcher_json(x) for x in catalog.list_researchers()])

    @api.post("/researchers")
    @require(ROLE_ADMIN)
    def add_researcher():
        body = _payload()
        created = catalog.add_researcher(
            SaveResearcherRequest(
                str(_required(body, "full_name")), str(body.get("organization") or "")
            )
        )
        return jsonify(_researcher_json(created)), 201

    # --- наблюдения и аналитика (исследователь) ---
    @api.get("/observations")
    @require(ROLE_RESEARCHER)
    def list_observations():
        return jsonify([_observation_json(o) for o in observations.list_observations()])

    @api.post("/observations")
    @require(ROLE_RESEARCHER)
    def add_observation():
        body = _payload()
        created = observations.create_observation(
            CreateObservationRequest(
                species_id=_as_int(_required(body, "species_id"), "species_id"),
                location_id=_as_int(_required(body, "location_id"), "location_id"),
                researcher_id=_as_int(_required(body, "researcher_id"), "researcher_id"),
                observation_date=_as_date(_required(body, "observation_date"), "observation_date"),
                individuals_count=_as_int(_required(body, "individuals_count"), "individuals_count"),
                notes=body.get("notes"),
            )
        )
        return jsonify(_observation_json(created)), 201

    @api.get("/analytics/population")
    @require(ROLE_RESEARCHER)
    def population_analysis():
        args = request.args
        location = args.get("location_id")
        result = analytics.analyze_population(
            PopulationAnalysisRequest(
                species_id=_as_int(args.get("species_id"), "species_id"),
                date_from=_as_date(args.get("date_from"), "date_from"),
                date_to=_as_date(args.get("date_to"), "date_to"),
                location_id=_as_int(location, "location_id") if location else None,
            )
        )
        return jsonify(
            records_count=result.records_count,
            has_trend=result.has_trend,
            warning=result.warning_message,
            rows=[{"date": d.isoformat(), "population_size": n} for d, n in result.rows],
        )

    return api
