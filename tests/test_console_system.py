from pathlib import Path
from typing import Iterator

import pytest

from wildlife_business.exceptions import ValidationError
from wildlife_app.main import build_app
from wildlife_ui.console_app import ConsoleApp
from wildlife_ui.io import IUserIO


class ScriptedIO(IUserIO):
    def __init__(self, answers: list[str]) -> None:
        self._answers = iter(answers)
        self.output: list[str] = []

    def write(self, text: str) -> None:
        self.output.append(text)

    def read(self, prompt: str) -> str:
        self.output.append(prompt)
        return next(self._answers)

    def text(self) -> str:
        return "\n".join(self.output)


@pytest.fixture
def io() -> ScriptedIO:
    return ScriptedIO([])


@pytest.fixture
def app(tmp_path: Path, io: ScriptedIO) -> Iterator[ConsoleApp]:
    console, repo = build_app(tmp_path / "wildlife.db", io)
    yield console
    repo.close()


def _fill_catalog(app: ConsoleApp, io: ScriptedIO) -> None:
    io._answers = iter(["Ursus arctos", "Бурый медведь"])
    app.add_species()
    io._answers = iter(["Заповедник", "Карелия"])
    app.add_location()
    io._answers = iter(["Иванов И.И.", "ИУ7"])
    app.add_researcher()


def test_system_admin_manages_species_and_locations(app: ConsoleApp, io: ScriptedIO) -> None:
    io._answers = iter(["Canis lupus", "Волк"])
    app.add_species()
    io._answers = iter(["1", "Canis lupus", "Серый волк"])
    app.edit_species()
    io._answers = iter(["Лапландия", "Мурманская область"])
    app.add_location()
    app.list_species()
    app.list_locations()

    log = io.text()
    assert "Вид сохранён, id=1" in log
    assert "Серый волк" in log
    assert "Локация сохранена, id=1" in log


def test_system_researcher_adds_and_lists_observation(app: ConsoleApp, io: ScriptedIO) -> None:
    _fill_catalog(app, io)
    io._answers = iter(["1", "1", "1", "2026-03-01", "7", "у реки"])
    app.add_observation()
    app.list_observations()

    log = io.text()
    assert "Наблюдение сохранено, id=1" in log
    assert "2026-03-01" in log
    assert "7" in log


def test_system_population_analysis_after_observation(app: ConsoleApp, io: ScriptedIO) -> None:
    _fill_catalog(app, io)
    io._answers = iter(["1", "1", "1", "2026-04-10", "12", ""])
    app.add_observation()
    io._answers = iter(["", "1", "2026-01-01", "2026-12-31"])
    app.analyze_population()

    log = io.text()
    assert "Записей: 1" in log
    assert "2026-04-10: 12" in log
    assert "Недостаточно данных для тренда" in log


def test_system_rejects_future_observation_date(app: ConsoleApp, io: ScriptedIO) -> None:
    _fill_catalog(app, io)
    io._answers = iter(["1", "1", "1", "2099-01-01", "1", ""])

    with pytest.raises(ValidationError, match="будущем"):
        app.add_observation()
