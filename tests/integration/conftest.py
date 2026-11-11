"""Integration-этап: настоящий файловый SQLite, поднятый скриптами db/sql/*.sql.

Жизненный цикл отдельного инстанса хранилища:
  1. init      — 01_schema.sql → 02_seed.sql в уникальный файл прогона;
  2. verify    — состояние совпадает с эталоном из тех же скриптов;
  3. тест      — работает с хранилищем через SqliteRepository и сервисы;
  4. rollback  — 90_rollback.sql → 02_seed.sql после КАЖДОГО теста, в т.ч. упавшего;
  5. verify    — после отката хранилище снова эталонное (иначе тест помечается ошибкой).

WILDLIFE_IT_DB=/path/to.db — использовать постоянный инстанс (проверка повторного прогона в CI):
перед стартом он обязан быть в эталонном состоянии, после прогона остаётся на месте.
Без переменной каждый запуск получает свой файл в tmp — разработчики не мешают друг другу.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

import allure
import pytest

from db import dbctl
from wildlife_business.analytics_service import AnalyticsService
from wildlife_business.catalog_service import CatalogService
from wildlife_business.observation_service import ObservationService
from wildlife_data.sqlite_repository import SqliteRepository

IT_DB_ENV = "WILDLIFE_IT_DB"


@dataclass(frozen=True)
class ItStorage:
    path: Path
    reference: dbctl.StorageState
    persistent: bool


@pytest.fixture(scope="session")
def storage(tmp_path_factory: pytest.TempPathFactory):
    reference = dbctl.reference_state()
    shared = os.environ.get(IT_DB_ENV, "").strip()
    if shared:
        path = Path(shared)
        if path.exists():
            # Предыдущий прогон обязан был вернуть хранилище в исходное состояние.
            dbctl.verify(path, reference)
        else:
            dbctl.init(path)
    else:
        path = tmp_path_factory.mktemp("wildlife-it") / f"wildlife-it-{uuid.uuid4().hex[:12]}.db"
        dbctl.init(path)
    dbctl.verify(path, reference)

    instance = ItStorage(path=path, reference=reference, persistent=bool(shared))
    try:
        yield instance
    finally:
        dbctl.rollback(path)
        dbctl.verify(path, reference)
        if not instance.persistent:
            path.unlink(missing_ok=True)


@pytest.fixture
def repository(storage: ItStorage):
    """Репозиторий над тестовым инстансом; после теста — принудительный откат и проверка."""
    # Имя файла уникально для прогона, поэтому в параметры Allure его не кладём:
    # иначе historyId менялся бы каждый запуск и тренды не связывались.
    allure.attach(str(storage.path), name="Инстанс хранилища", attachment_type=allure.attachment_type.TEXT)
    repo = SqliteRepository(storage.path)
    try:
        yield repo
    finally:
        repo.close()
        dbctl.rollback(storage.path)
        dbctl.verify(storage.path, storage.reference)


@pytest.fixture
def catalog(repository: SqliteRepository) -> CatalogService:
    return CatalogService(repository)


@pytest.fixture
def observations(repository: SqliteRepository) -> ObservationService:
    return ObservationService(repository)


@pytest.fixture
def analytics(repository: SqliteRepository) -> AnalyticsService:
    return AnalyticsService(repository)
