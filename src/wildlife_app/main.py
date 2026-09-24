"""Точка сборки: UI + бизнес-логика + доступ к данным + конфиг + логи."""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from wildlife_app.config import AppConfig, default_config_path, load_config
from wildlife_app.logging_setup import setup_logging
from wildlife_business.analytics_service import AnalyticsService
from wildlife_business.catalog_service import CatalogService
from wildlife_business.observation_service import ObservationService
from wildlife_data.sqlite_repository import SqliteRepository
from wildlife_gui.flask_app import create_flask_app
from wildlife_ui.console_app import ConsoleApp
from wildlife_ui.io import ConsoleIO, IUserIO

logger = logging.getLogger("wildlife.app")


@dataclass
class WiredApp:
    repository: SqliteRepository
    observations: ObservationService
    catalog: CatalogService
    analytics: AnalyticsService


def wire_components(
    database: str | Path,
    min_records_for_trend: int = 5,
) -> WiredApp:
    repo = SqliteRepository(database)
    return WiredApp(
        repository=repo,
        observations=ObservationService(repo),
        catalog=CatalogService(repo),
        analytics=AnalyticsService(repo, min_records_for_trend=min_records_for_trend),
    )


def build_app(
    database: str | Path,
    io: IUserIO | None = None,
    min_records_for_trend: int = 5,
) -> tuple[ConsoleApp, SqliteRepository]:
    wired = wire_components(database, min_records_for_trend=min_records_for_trend)
    app = ConsoleApp(
        wired.observations,
        wired.catalog,
        wired.analytics,
        io or ConsoleIO(),
    )
    return app, wired.repository


def run_console(wired: WiredApp, io: IUserIO | None = None) -> None:
    ConsoleApp(wired.observations, wired.catalog, wired.analytics, io or ConsoleIO()).run()


def run_gui(wired: WiredApp, config: AppConfig) -> None:
    flask_app = create_flask_app(
        wired.observations,
        wired.catalog,
        wired.analytics,
        secret_key=config.gui_secret_key,
    )
    logger.info("Запущен GUI: http://%s:%s", config.gui_host, config.gui_port)
    flask_app.run(
        host=config.gui_host,
        port=config.gui_port,
        debug=False,
        use_reloader=False,
    )


def run_with_config(
    config: AppConfig,
    io: IUserIO | None = None,
    ui: str = "console",
) -> None:
    setup_logging(config.log_file, config.log_level)
    logger.info(
        "Приложение запущено: ui=%s db=%s trend=%s log=%s",
        ui,
        config.database_path,
        config.min_records_for_trend,
        config.log_file,
    )
    wired = wire_components(
        config.database_path,
        min_records_for_trend=config.min_records_for_trend,
    )
    try:
        if ui == "gui":
            run_gui(wired, config)
        else:
            run_console(wired, io)
    except Exception:
        logger.exception("Фатальная ошибка приложения")
        raise
    finally:
        wired.repository.close()
        logger.info("Приложение остановлено")


def main(argv: list[str] | None = None) -> None:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Wildlife Monitoring — консоль или GUI")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Путь к config.ini",
    )
    parser.add_argument(
        "--ui",
        choices=("console", "gui"),
        default="console",
        help="Технологический UI (console) или графический MVC (gui)",
    )
    args = parser.parse_args(argv)
    config_path = args.config or default_config_path()
    config = load_config(config_path)
    run_with_config(config, ui=args.ui)


if __name__ == "__main__":
    main()
