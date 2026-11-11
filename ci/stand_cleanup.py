"""Завершение всех активных сессий стенда после E2E (успешного или аварийного).

Запускается внутри контейнера стенда: python ci/stand_cleanup.py [base_url]
"""
from __future__ import annotations

import json
import sys
import urllib.request


def _call(method: str, url: str, body: dict | None = None, token: str | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else {}


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000").rstrip("/") + "/api/v1"
    before = _call("GET", f"{base}/health")["active_sessions"]
    token = _call("POST", f"{base}/session", {"role": "admin"})["token"]
    closed = _call("DELETE", f"{base}/sessions", token=token)["closed"]
    after = _call("GET", f"{base}/health")["active_sessions"]
    print(f"[stand] сессии: было {before}, завершено {closed} (включая служебную), осталось {after}")
    return 0 if after == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
