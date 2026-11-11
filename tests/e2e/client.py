"""Минимальный HTTP-клиент для E2E: stdlib urllib, каждый обмен прикладывается в Allure."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

import allure


@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: Any


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.opened_tokens: list[str] = []

    def call(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
        token: Optional[str] = None,
    ) -> ApiResponse:
        url = f"{self.base_url}/api/v1{path}"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status, raw = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
        text = raw.decode("utf-8") if raw else ""
        parsed = json.loads(text) if text else None
        allure.attach(
            f"{method} {url}\n{json.dumps(body, ensure_ascii=False, indent=2) if body else ''}\n\n"
            f"HTTP {status}\n{json.dumps(parsed, ensure_ascii=False, indent=2) if parsed is not None else ''}",
            name=f"{method} {path} → {status}",
            attachment_type=allure.attachment_type.TEXT,
        )
        return ApiResponse(status, parsed)

    def wait_until_ready(self, timeout: float = 60.0) -> None:
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"{self.base_url}/api/v1/health", timeout=3) as resp:
                    if resp.status == 200:
                        return
            except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
                last_error = exc
            time.sleep(1)
        raise RuntimeError(f"Стенд {self.base_url} не ответил за {timeout:.0f} с: {last_error}")

    def login(self, role: str) -> str:
        response = self.call("POST", "/session", {"role": role})
        assert response.status == 201, response
        token = response.body["token"]
        self.opened_tokens.append(token)
        return token

    def close_opened_sessions(self) -> list[str]:
        """Завершает все сессии, открытые этим прогоном; возвращает токены, которые остались живы."""
        alive = []
        for token in self.opened_tokens:
            self.call("DELETE", "/session", token=token)
            if self.call("GET", "/species", token=token).status != 401:
                alive.append(token)
        self.opened_tokens.clear()
        return alive
