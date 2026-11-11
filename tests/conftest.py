"""Общая настройка всех этапов: unit → integration → e2e.

* каждый тест получает маркер и Allure-метку своего этапа по каталогу;
* если этап в CI не запускался (упал предыдущий), он прогоняется с
  WILDLIFE_STAGE_SKIPPED — все тесты попадают в отчёт как skipped;
* в сырые результаты Allure кладутся environment.properties и categories.json.
"""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

import allure
import pytest

STAGES = ("unit", "integration", "e2e")
STAGE_TITLES = {
    "unit": "1. Unit",
    "integration": "2. Integration",
    "e2e": "3. E2E",
}
SKIP_ENV = "WILDLIFE_STAGE_SKIPPED"
_TESTS_DIR = Path(__file__).resolve().parent


def stage_of(item: pytest.Item) -> str | None:
    try:
        relative = Path(str(item.path)).resolve().relative_to(_TESTS_DIR)
    except ValueError:
        return None
    head = relative.parts[0] if relative.parts else ""
    return head if head in STAGES else None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    skip_reason = os.environ.get(SKIP_ENV, "").strip()
    for item in items:
        stage = stage_of(item)
        if stage:
            item.add_marker(getattr(pytest.mark, stage))
            item.add_marker(allure.parent_suite(STAGE_TITLES[stage]))
            item.add_marker(allure.tag(stage))
        if skip_reason:
            item.add_marker(pytest.mark.skip(reason=skip_reason))


def _collected_stages(session: pytest.Session) -> str:
    stages = sorted({stage_of(item) or "other" for item in session.items})
    return ", ".join(stages) or "none"


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Кладёт окружение и категории в каталог сырых результатов Allure."""
    report_dir = getattr(session.config.option, "allure_report_dir", None)
    if not report_dir:
        return

    target = Path(report_dir)
    target.mkdir(parents=True, exist_ok=True)
    properties = "\n".join(
        (
            "Project=Wildlife Monitoring DB",
            f"Python={platform.python_version()}",
            f"OS={platform.system()} {platform.release()}",
            "Framework=pytest",
            "Pipeline=unit -> integration -> e2e",
            f"Stages={_collected_stages(session)}",
            "Storage=SQLite (unit: :memory:, integration: отдельный файл из db/*.sql, e2e: стенд в Docker)",
            f"E2E.URL={os.environ.get('WILDLIFE_E2E_URL', 'not used')}",
            f"CI={os.environ.get('GITHUB_ACTIONS', 'false')}",
            "",
        )
    )
    (target / "environment.properties").write_text(properties, encoding="utf-8")

    categories = _TESTS_DIR.parent / "allure" / "categories.json"
    if categories.is_file():
        shutil.copyfile(categories, target / "categories.json")
