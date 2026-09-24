"""Конфигурация приложения (ini): БД и параметры бизнес-логики."""
from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    min_records_for_trend: int
    log_level: str
    log_file: Path
    gui_host: str
    gui_port: int
    gui_secret_key: str


def _sqlite_path(connection_string: str, base_dir: Path) -> Path:
    value = connection_string.strip()
    prefix = "sqlite:///"
    if value.lower().startswith(prefix):
        value = value[len(prefix) :]
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return path


def load_config(path: Path) -> AppConfig:
    parser = configparser.ConfigParser()
    if not path.is_file():
        raise FileNotFoundError(f"Не найден файл конфигурации: {path}")
    read = parser.read(path, encoding="utf-8")
    if not read:
        raise FileNotFoundError(f"Не удалось прочитать конфигурацию: {path}")

    base_dir = path.parent
    connection = parser.get("database", "connection_string", fallback="sqlite:///wildlife.db")
    min_trend = parser.getint("business", "min_records_for_trend", fallback=5)
    log_level = parser.get("logging", "level", fallback="INFO")
    log_file_raw = parser.get("logging", "file", fallback="logs/app.log")
    log_file = Path(log_file_raw)
    if not log_file.is_absolute():
        log_file = base_dir / log_file
    return AppConfig(
        database_path=_sqlite_path(connection, base_dir),
        min_records_for_trend=min_trend,
        log_level=log_level.upper(),
        log_file=log_file,
        gui_host=parser.get("gui", "host", fallback="127.0.0.1"),
        gui_port=parser.getint("gui", "port", fallback=5000),
        gui_secret_key=parser.get("gui", "secret_key", fallback="wildlife-local"),
    )


def default_config_path() -> Path:
    candidates = [
        Path.cwd() / "config.ini",
        Path(__file__).resolve().parents[2] / "config.ini",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]
