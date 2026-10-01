"""Технологический UI: консольное меню поверх тех же сервисов, что и GUI."""
from collections.abc import Callable
import logging

from wildlife_business.analytics_service import AnalyticsService
from wildlife_business.catalog_service import CatalogService
from wildlife_business.exceptions import BusinessError
from wildlife_business.observation_service import ObservationService
from wildlife_business.dto import (
    CreateObservationRequest,
    PopulationAnalysisRequest,
    SaveLocationRequest,
    SaveResearcherRequest,
    SaveSpeciesRequest,
)
from wildlife_ui.io import IUserIO
from wildlife_ui.parsing import parse_date, parse_int, parse_optional_int, parse_optional_text

logger = logging.getLogger("wildlife.ui")
PROMPT_CHOICE = "Выбор: "
PROMPT_SPECIES_ID = "ID вида: "


class ConsoleApp:
    def __init__(
        self,
        observations: ObservationService,
        catalog: CatalogService,
        analytics: AnalyticsService,
        io: IUserIO,
    ) -> None:
        self._observations = observations
        self._catalog = catalog
        self._analytics = analytics
        self._io = io

    def run(self) -> None:
        logger.info("Пользователь запустил технологический UI")
        self._io.write("Wildlife Monitoring DB — технологический UI")
        while True:
            self._io.write("")
            self._io.write("Роль: 1) Исследователь  2) Администратор  0) Выход")
            choice = self._io.read(PROMPT_CHOICE).strip()
            if choice == "0":
                logger.info("Пользователь вышел из приложения")
                self._io.write("Выход.")
                return
            if choice == "1":
                logger.info("Пользователь выбрал роль: исследователь")
                self._researcher_menu()
            elif choice == "2":
                logger.info("Пользователь выбрал роль: администратор")
                self._admin_menu()
            else:
                logger.warning("Неизвестная команда роли: %s", choice)
                self._io.write("Неизвестная команда.")

    def add_observation(self) -> None:
        self._print_species()
        self._print_locations()
        self._print_researchers()
        request = CreateObservationRequest(
            species_id=parse_int(self._io.read(PROMPT_SPECIES_ID), "вид"),
            location_id=parse_int(self._io.read("ID локации: "), "локация"),
            researcher_id=parse_int(self._io.read("ID исследователя: "), "исследователь"),
            observation_date=parse_date(self._io.read("Дата (ГГГГ-ММ-ДД): "), "дата"),
            individuals_count=parse_int(self._io.read("Количество особей: "), "количество"),
            notes=parse_optional_text(self._io.read("Заметки (пусто — нет): ")),
        )
        saved = self._observations.create_observation(request)
        logger.info(
            "Пользователь добавил наблюдение id=%s species=%s location=%s count=%s",
            saved.id,
            saved.species_id,
            saved.location_id,
            saved.individuals_count,
        )
        self._io.write(f"Наблюдение сохранено, id={saved.id}")

    def list_observations(self) -> None:
        rows = self._observations.list_observations()
        if not rows:
            self._io.write("Наблюдений пока нет.")
            return
        self._io.write("id | дата | вид | локация | исследователь | особей | заметки")
        for item in rows:
            notes = item.notes or ""
            self._io.write(
                f"{item.id} | {item.observation_date.isoformat()} | "
                f"{item.species_id} | {item.location_id} | {item.researcher_id} | "
                f"{item.individuals_count} | {notes}"
            )

    def analyze_population(self) -> None:
        self._print_species()
        self._print_locations()
        location_id = parse_optional_int(
            self._io.read("ID локации (пусто — все): "), "локация"
        )
        request = PopulationAnalysisRequest(
            species_id=parse_int(self._io.read(PROMPT_SPECIES_ID), "вид"),
            date_from=parse_date(self._io.read("Дата с (ГГГГ-ММ-ДД): "), "дата начала"),
            date_to=parse_date(self._io.read("Дата по (ГГГГ-ММ-ДД): "), "дата окончания"),
            location_id=location_id,
        )
        result = self._analytics.analyze_population(request)
        logger.info(
            "Пользователь запросил аналитику species=%s from=%s to=%s records=%s",
            request.species_id,
            request.date_from,
            request.date_to,
            result.records_count,
        )
        self._io.write(f"Записей: {result.records_count}, тренд: {result.has_trend}")
        if result.warning_message:
            self._io.write(result.warning_message)
        for record_date, size in result.rows:
            self._io.write(f"{record_date.isoformat()}: {size}")

    def add_species(self) -> None:
        saved = self._catalog.add_species(
            SaveSpeciesRequest(
                self._io.read("Научное название: "),
                self._io.read("Обычное название: "),
            )
        )
        logger.info("Пользователь добавил вид id=%s (%s)", saved.id, saved.scientific_name)
        self._io.write(f"Вид сохранён, id={saved.id} ({saved.scientific_name})")

    def edit_species(self) -> None:
        self._print_species()
        species_id = parse_int(self._io.read(PROMPT_SPECIES_ID), "вид")
        updated = self._catalog.update_species(
            species_id,
            SaveSpeciesRequest(
                self._io.read("Новое научное название: "),
                self._io.read("Новое обычное название: "),
            ),
        )
        logger.info("Пользователь изменил вид id=%s", species_id)
        self._io.write(f"Вид изменён: {updated.scientific_name} / {updated.common_name}")

    def list_species(self) -> None:
        self._print_species()

    def add_location(self) -> None:
        saved = self._catalog.add_location(
            SaveLocationRequest(
                self._io.read("Название локации: "),
                self._io.read("Регион (пусто — нет): "),
            )
        )
        logger.info("Пользователь добавил локацию id=%s (%s)", saved.id, saved.name)
        self._io.write(f"Локация сохранена, id={saved.id} ({saved.name})")

    def list_locations(self) -> None:
        self._print_locations()

    def add_researcher(self) -> None:
        saved = self._catalog.add_researcher(
            SaveResearcherRequest(
                self._io.read("ФИО: "),
                self._io.read("Организация (пусто — нет): "),
            )
        )
        logger.info("Пользователь добавил исследователя id=%s", saved.id)
        self._io.write(f"Исследователь сохранён, id={saved.id} ({saved.full_name})")

    def list_researchers(self) -> None:
        self._print_researchers()

    def _researcher_menu(self) -> None:
        while True:
            self._io.write("")
            self._io.write(
                "Исследователь: 1) Добавить наблюдение  2) Список наблюдений  "
                "3) Аналитика  0) Назад"
            )
            choice = self._io.read(PROMPT_CHOICE).strip()
            if choice == "0":
                return
            actions = {
                "1": self.add_observation,
                "2": self.list_observations,
                "3": self.analyze_population,
            }
            self._dispatch(actions.get(choice))

    def _admin_menu(self) -> None:
        while True:
            self._io.write("")
            self._io.write(
                "Администратор: 1) Добавить вид  2) Изменить вид  3) Список видов  "
                "4) Добавить локацию  5) Список локаций  "
                "6) Добавить исследователя  7) Список исследователей  0) Назад"
            )
            choice = self._io.read(PROMPT_CHOICE).strip()
            if choice == "0":
                return
            actions = {
                "1": self.add_species,
                "2": self.edit_species,
                "3": self.list_species,
                "4": self.add_location,
                "5": self.list_locations,
                "6": self.add_researcher,
                "7": self.list_researchers,
            }
            self._dispatch(actions.get(choice))

    def _dispatch(self, action: Callable[[], None] | None) -> None:
        if action is None:
            self._io.write("Неизвестная команда.")
            return
        try:
            action()
        except BusinessError as exc:
            logger.warning("Исключение бизнес-логики: %s", exc, exc_info=True)
            self._io.write(f"Ошибка: {exc}")
        except Exception as exc:
            logger.exception("Необработанное исключение в UI")
            self._io.write(f"Ошибка хранения: {exc}")

    def _print_species(self) -> None:
        rows = self._catalog.list_species()
        if not rows:
            self._io.write("Справочник видов пуст.")
            return
        self._io.write("Виды: id | научное имя | обычное имя")
        for item in rows:
            self._io.write(f"{item.id} | {item.scientific_name} | {item.common_name}")

    def _print_locations(self) -> None:
        rows = self._catalog.list_locations()
        if not rows:
            self._io.write("Справочник локаций пуст.")
            return
        self._io.write("Локации: id | название | регион")
        for item in rows:
            region = item.region or ""
            self._io.write(f"{item.id} | {item.name} | {region}")

    def _print_researchers(self) -> None:
        rows = self._catalog.list_researchers()
        if not rows:
            self._io.write("Список исследователей пуст.")
            return
        self._io.write("Исследователи: id | ФИО | организация")
        for item in rows:
            org = item.organization or ""
            self._io.write(f"{item.id} | {item.full_name} | {org}")
