from pathlib import Path

import pytest

from wildlife_app.main import wire_components
from wildlife_gui.controllers import (
    AnalyticsController,
    CatalogController,
    ObservationController,
    RoleController,
)
from wildlife_gui.flask_app import create_flask_app
from wildlife_gui.viewmodels import ROLE_ADMIN, ROLE_RESEARCHER


@pytest.fixture
def wired(tmp_path: Path):
    app = wire_components(tmp_path / "wildlife.db")
    yield app
    app.repository.close()


@pytest.fixture
def catalog_ctl(wired) -> CatalogController:
    return CatalogController(wired.catalog)


@pytest.fixture
def obs_ctl(wired) -> ObservationController:
    return ObservationController(wired.observations, wired.catalog)


@pytest.fixture
def analytics_ctl(wired) -> AnalyticsController:
    return AnalyticsController(wired.analytics, wired.catalog)


def _fill_catalog(catalog_ctl: CatalogController) -> None:
    assert catalog_ctl.add_species(
        {"scientific_name": "Ursus arctos", "common_name": "Бурый медведь"}
    ).ok
    assert catalog_ctl.add_location({"name": "Заповедник", "region": "Карелия"}).ok
    assert catalog_ctl.add_researcher(
        {"full_name": "Иванов И.И.", "organization": "ИУ7"}
    ).ok


def test_role_controller_accepts_known_roles() -> None:
    ctl = RoleController()
    assert ctl.select(ROLE_RESEARCHER).ok
    assert ctl.select(ROLE_ADMIN).ok
    assert not ctl.select("unknown").ok


def test_gui_admin_manages_species_and_locations(catalog_ctl: CatalogController) -> None:
    added = catalog_ctl.add_species({"scientific_name": "Canis lupus", "common_name": "Волк"})
    assert added.ok
    assert "id=1" in added.message
    updated = catalog_ctl.update_species(
        1, {"scientific_name": "Canis lupus", "common_name": "Серый волк"}
    )
    assert updated.ok
    assert "Серый волк" in updated.message
    loc = catalog_ctl.add_location({"name": "Лапландия", "region": "Мурманская область"})
    assert loc.ok
    names = [row.common_name for row in catalog_ctl.species_page().rows]
    assert "Серый волк" in names
    assert catalog_ctl.list_locations()[0].name == "Лапландия"


def test_gui_researcher_adds_and_lists_observation(
    catalog_ctl: CatalogController, obs_ctl: ObservationController
) -> None:
    _fill_catalog(catalog_ctl)
    result = obs_ctl.create(
        {
            "species_id": "1",
            "location_id": "1",
            "researcher_id": "1",
            "observation_date": "2026-03-01",
            "individuals_count": "7",
            "notes": "у реки",
        }
    )
    assert result.ok
    rows = obs_ctl.list_rows()
    assert len(rows) == 1
    assert rows[0].date == "2026-03-01"
    assert rows[0].count == 7
    assert "Бурый медведь" in rows[0].species


def test_gui_population_analysis_after_observation(
    catalog_ctl: CatalogController,
    obs_ctl: ObservationController,
    analytics_ctl: AnalyticsController,
) -> None:
    _fill_catalog(catalog_ctl)
    obs_ctl.create(
        {
            "species_id": "1",
            "location_id": "1",
            "researcher_id": "1",
            "observation_date": "2026-04-10",
            "individuals_count": "12",
            "notes": "",
        }
    )
    state = analytics_ctl.page(
        {
            "species_id": "1",
            "location_id": "",
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
        }
    )
    assert state.error is None
    assert state.records_count == 1
    assert state.rows[0].date == "2026-04-10"
    assert state.rows[0].size == 12
    assert state.warning == "Недостаточно данных для тренда"
    assert not state.chart.line_points


def test_gui_rejects_future_observation_date(
    catalog_ctl: CatalogController, obs_ctl: ObservationController
) -> None:
    _fill_catalog(catalog_ctl)
    result = obs_ctl.create(
        {
            "species_id": "1",
            "location_id": "1",
            "researcher_id": "1",
            "observation_date": "2099-01-01",
            "individuals_count": "1",
            "notes": "",
        }
    )
    assert not result.ok
    assert "будущем" in result.message


def test_flask_http_flow(wired) -> None:
    app = create_flask_app(wired.observations, wired.catalog, wired.analytics)
    app.config["TESTING"] = True
    client = app.test_client()

    home = client.get("/")
    assert home.status_code == 200
    assert "Исследователь" in home.get_data(as_text=True)

    client.post("/role", data={"role": "admin"}, follow_redirects=True)
    client.post(
        "/species",
        data={"scientific_name": "Lynx lynx", "common_name": "Рысь"},
        follow_redirects=True,
    )
    client.post(
        "/locations",
        data={"name": "Тайга", "region": "Сибирь"},
        follow_redirects=True,
    )
    client.post(
        "/researchers",
        data={"full_name": "Петров П.П.", "organization": ""},
        follow_redirects=True,
    )

    client.post("/logout")
    client.post("/role", data={"role": "researcher"}, follow_redirects=True)
    created = client.post(
        "/observations/new",
        data={
            "species_id": "1",
            "location_id": "1",
            "researcher_id": "1",
            "observation_date": "2026-05-01",
            "individuals_count": "3",
            "notes": "",
        },
        follow_redirects=True,
    )
    page = created.get_data(as_text=True)
    assert "Наблюдение сохранено" in page
    assert "2026-05-01" in page
    assert "Рысь" in page
