"""Реестр активных сессий HTTP API: токен → роль. Хранится в памяти процесса."""
from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ApiSession:
    token: str
    role: str


class SessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, ApiSession] = {}
        self._lock = threading.Lock()

    def open(self, role: str) -> ApiSession:
        session = ApiSession(secrets.token_urlsafe(24), role)
        with self._lock:
            self._sessions[session.token] = session
        return session

    def get(self, token: str) -> Optional[ApiSession]:
        with self._lock:
            return self._sessions.get(token)

    def close(self, token: str) -> bool:
        with self._lock:
            return self._sessions.pop(token, None) is not None

    def close_all(self) -> int:
        with self._lock:
            closed = len(self._sessions)
            self._sessions.clear()
            return closed

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)
