"""Скрипт 01_schema.sql и встроенная схема SqliteRepository описывают одну и ту же БД."""
import sqlite3
from contextlib import closing

import allure

from db import dbctl
from wildlife_data.sqlite_repository import SqliteRepository

pytestmark = [
    allure.epic("Мониторинг популяции диких животных"),
    allure.feature("Integration: развёртывание хранилища"),
]


def _columns(db_path) -> dict[str, list[tuple]]:
    # closing(): контекст sqlite3.Connection только коммитит, но не закрывает соединение.
    with closing(sqlite3.connect(str(db_path))) as conn:
        return {
            table: [tuple(row) for row in conn.execute(f"PRAGMA table_info({table})")]
            for table in dbctl.TABLES
        }


@allure.story("Развёртывание хранилища")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Таблицы из скриптов совпадают со схемой, которую создаёт приложение")
def test_schema_script_matches_repository_schema(storage, tmp_path) -> None:
    # arrange
    app_db = tmp_path / "created-by-repository.db"

    with allure.step("act: дать приложению создать схему в пустом файле"):
        with SqliteRepository(app_db) as repo:
            repo.list_species()
        from_app = _columns(app_db)
        from_scripts = _columns(storage.path)

    with allure.step("assert: набор таблиц и колонок одинаков"):
        assert from_scripts == from_app
        assert all(from_scripts[table] for table in dbctl.TABLES)
