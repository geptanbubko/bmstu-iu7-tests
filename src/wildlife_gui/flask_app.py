"""Flask-адаптер View: HTTP → контроллеры MVC → шаблоны Jinja2."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Callable

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.exceptions import HTTPException

from wildlife_business.analytics_service import AnalyticsService
from wildlife_business.catalog_service import CatalogService
from wildlife_business.observation_service import ObservationService
from wildlife_gui.api import create_api_blueprint
from wildlife_gui.sessions import SessionRegistry
from wildlife_gui.controllers import (
    AnalyticsController,
    CatalogController,
    ObservationController,
    RoleController,
)
from wildlife_gui.viewmodels import ROLE_ADMIN, ROLE_RESEARCHER

logger = logging.getLogger("wildlife.gui")


@dataclass
class _Gui:
    role: RoleController
    observations: ObservationController
    catalog: CatalogController
    analytics: AnalyticsController


def create_flask_app(
    observations: ObservationService,
    catalog: CatalogService,
    analytics: AnalyticsService,
    *,
    secret_key: str = "wildlife-local",
) -> Flask:
    pkg = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(pkg / "templates"),
        static_folder=str(pkg / "static"),
    )
    app.secret_key = secret_key
    app.config["WTF_CSRF_ENABLED"] = True
    csrf = CSRFProtect(app)

    # JSON API для E2E/Postman: без cookie-сессий, поэтому CSRF к нему не применяется.
    sessions = SessionRegistry()
    app.extensions["wildlife_sessions"] = sessions
    api = create_api_blueprint(observations, catalog, analytics, sessions)
    csrf.exempt(api)
    app.register_blueprint(api)

    gui = _Gui(
        role=RoleController(),
        observations=ObservationController(observations, catalog),
        catalog=CatalogController(catalog),
        analytics=AnalyticsController(analytics, catalog),
    )
    _register_context(app, gui)
    _register_session_routes(app, gui)
    _register_researcher_routes(app, gui)
    _register_admin_routes(app, gui)
    _register_error_handler(app)
    return app


def _require_roles(*roles: str) -> Callable:
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                flash("Сначала выберите роль", "error")
                return redirect(url_for("home"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _register_context(app: Flask, gui: _Gui) -> None:
    @app.context_processor
    def inject_ui_state():
        role = session.get("role")
        return {
            "current_role": role,
            "current_role_label": gui.role.label(role),
        }


def _register_session_routes(app: Flask, gui: _Gui) -> None:
    @app.get("/")
    def home():
        return render_template("index.html", page="home")

    @app.post("/role")
    def select_role():
        role = (request.form.get("role") or "").strip()
        result = gui.role.select(role)
        if not result.ok:
            flash(result.message, "error")
            return redirect(url_for("home"))
        session["role"] = role
        flash(result.message, "ok")
        if role == ROLE_RESEARCHER:
            return redirect(url_for("observations"))
        return redirect(url_for("species"))

    @app.post("/logout")
    def logout():
        logger.info("Пользователь сменил роль")
        session.clear()
        return redirect(url_for("home"))


def _register_researcher_routes(app: Flask, gui: _Gui) -> None:
    @app.get("/observations")
    @_require_roles(ROLE_RESEARCHER)
    def observations():
        return render_template(
            "observations.html",
            page="observations",
            section="Наблюдения",
            rows=gui.observations.list_rows(),
        )

    @app.route("/observations/new", methods=["GET", "POST"])
    @_require_roles(ROLE_RESEARCHER)
    def observation_new():
        if request.method != "POST":
            return render_template(
                "observation_form.html",
                page="observation_new",
                section="Новое наблюдение",
                form=gui.observations.form_state(),
            )
        result = gui.observations.create(request.form)
        flash(result.message, "ok" if result.ok else "error")
        if result.ok:
            return redirect(url_for("observations"))
        return render_template(
            "observation_form.html",
            page="observation_new",
            section="Новое наблюдение",
            form=gui.observations.form_state(request.form),
        )

    @app.route("/analytics", methods=["GET", "POST"])
    @_require_roles(ROLE_RESEARCHER)
    def analytics_page():
        state = gui.analytics.page(request.form if request.method == "POST" else None)
        if state.error:
            flash(state.error, "error")
        return render_template(
            "analytics.html",
            page="analytics",
            section="Аналитика популяции",
            state=state,
        )


def _register_admin_routes(app: Flask, gui: _Gui) -> None:
    @app.get("/species")
    @_require_roles(ROLE_ADMIN)
    def species():
        return render_template(
            "species.html",
            page="species",
            section="Справочник видов",
            catalog=gui.catalog.species_page(),
        )

    @app.get("/species/<int:species_id>/edit")
    @_require_roles(ROLE_ADMIN)
    def species_edit(species_id: int):
        page_data = gui.catalog.species_page(species_id)
        if page_data.editing_id is None:
            flash("Вид не найден", "error")
            return redirect(url_for("species"))
        return render_template(
            "species.html",
            page="species",
            section="Изменение вида",
            catalog=page_data,
        )

    @app.post("/species")
    @_require_roles(ROLE_ADMIN)
    def species_add():
        result = gui.catalog.add_species(request.form)
        flash(result.message, "ok" if result.ok else "error")
        return redirect(url_for("species"))

    @app.post("/species/<int:species_id>")
    @_require_roles(ROLE_ADMIN)
    def species_update(species_id: int):
        result = gui.catalog.update_species(species_id, request.form)
        flash(result.message, "ok" if result.ok else "error")
        if result.ok:
            return redirect(url_for("species"))
        return redirect(url_for("species_edit", species_id=species_id))

    @app.get("/locations")
    @_require_roles(ROLE_ADMIN)
    def locations():
        return render_template(
            "locations.html",
            page="locations",
            section="Локации",
            rows=gui.catalog.list_locations(),
        )

    @app.post("/locations")
    @_require_roles(ROLE_ADMIN)
    def location_add():
        result = gui.catalog.add_location(request.form)
        flash(result.message, "ok" if result.ok else "error")
        return redirect(url_for("locations"))

    @app.get("/researchers")
    @_require_roles(ROLE_ADMIN)
    def researchers():
        return render_template(
            "researchers.html",
            page="researchers",
            section="Исследователи",
            rows=gui.catalog.list_researchers(),
        )

    @app.post("/researchers")
    @_require_roles(ROLE_ADMIN)
    def researcher_add():
        result = gui.catalog.add_researcher(request.form)
        flash(result.message, "ok" if result.ok else "error")
        return redirect(url_for("researchers"))


def _register_error_handler(app: Flask) -> None:
    @app.errorhandler(Exception)
    def unexpected_error(exc: Exception):
        if isinstance(exc, HTTPException):
            return exc
        logger.exception("Необработанное исключение в GUI")
        flash(f"Ошибка хранения: {exc}", "error")
        return redirect(url_for("home"))
