"""Unit-этап: SQLite :memory: для классической школы и подменённый connect для лондонской."""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from wildlife_data.sqlite_repository import SqliteRepository

# Настоящий connect, сохранённый до подмены: классические тесты открывают :memory:.
_REAL_SQLITE_CONNECT = sqlite3.connect


def _substituted_connection() -> MagicMock:
    connection = MagicMock(name="substituted_sqlite_connection")
    cursor = MagicMock(name="substituted_sqlite_cursor")
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    cursor.lastrowid = 1
    cursor.rowcount = 0
    connection.execute.return_value = cursor
    connection.cursor.return_value = cursor
    return connection


@pytest.fixture(scope="package", autouse=True)
def test_runtime():
    """Подменяет sqlite3.connect для файловых путей: файл БД не открывается.

    Область — пакет tests/unit: при выходе из пакета подмена снимается, поэтому
    integration-тесты (даже при перемешанном порядке) получают настоящий connect.
    """
    connection = _substituted_connection()

    def factory(database, *args, **kwargs):
        if database == ":memory:":
            raise AssertionError("In-memory SQLite через подмену connect запрещён")
        connection._opened_with = database
        return connection

    with patch("wildlife_data.sqlite_repository.sqlite3.connect", side_effect=factory) as connect:
        yield {"connect": connect, "connection": connection}
    connection.close()


@pytest.fixture
def substituted_connection(test_runtime):
    return test_runtime["connection"]


@pytest.fixture
def connect_spy(test_runtime):
    return test_runtime["connect"]


@pytest.fixture
def repository():
    """SQLite :memory: на один тест. Соединение закрывается после него."""
    repo = SqliteRepository(":memory:", connection_factory=_REAL_SQLITE_CONNECT)
    try:
        yield repo
    finally:
        repo.close()
