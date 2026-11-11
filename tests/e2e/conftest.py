"""E2E-этап: тесты ходят по HTTP в стенд, развёрнутый в Docker (docker-compose.test.yml).

WILDLIFE_E2E_URL — адрес стенда (в CI: http://app:5000 внутри сети compose).
После прогона — успешного или аварийного — закрываются все сессии, открытые тестами.
Откат хранилища стенда выполняется на уровне окружения: ci/stand.sh cleanup.
"""
from __future__ import annotations

import os
import uuid

import pytest

from tests.e2e.client import ApiClient

E2E_URL_ENV = "WILDLIFE_E2E_URL"


@pytest.fixture(scope="session")
def api():
    client = ApiClient(os.environ.get(E2E_URL_ENV, "http://localhost:5000"))
    client.wait_until_ready(timeout=float(os.environ.get("WILDLIFE_E2E_WAIT", "60")))
    try:
        yield client
    finally:
        alive = client.close_opened_sessions()
        assert not alive, f"Не удалось завершить сессии: {len(alive)}"


@pytest.fixture(scope="session")
def run_tag() -> str:
    """Уникальная метка прогона: данные разных разработчиков на одном стенде не пересекаются."""
    return os.environ.get("WILDLIFE_RUN_TAG") or uuid.uuid4().hex[:8]
