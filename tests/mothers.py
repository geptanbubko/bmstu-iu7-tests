"""Object Mother: готовые типовые объекты для тестов, выдаются по говорящему имени."""
from __future__ import annotations

from datetime import date

from wildlife_business.dto import SaveLocationRequest, SaveResearcherRequest, SaveSpeciesRequest
from wildlife_business.entities import Observation, PopulationRecord, Species


class ObjectMother:
    # --- запросы справочника ---
    @staticmethod
    def wolf() -> SaveSpeciesRequest:
        return SaveSpeciesRequest("Canis lupus", "Волк")

    @staticmethod
    def lynx() -> SaveSpeciesRequest:
        return SaveSpeciesRequest("Lynx lynx", "Рысь")

    @staticmethod
    def brown_bear() -> SaveSpeciesRequest:
        return SaveSpeciesRequest("Ursus arctos", "Бурый медведь")

    @staticmethod
    def lapland() -> SaveLocationRequest:
        return SaveLocationRequest("Лапландия", "Мурманская область")

    @staticmethod
    def karelia_reserve() -> SaveLocationRequest:
        return SaveLocationRequest("Заповедник", "Карелия")

    @staticmethod
    def petrov() -> SaveResearcherRequest:
        return SaveResearcherRequest("Петров П.П.", "ИУ7")

    @staticmethod
    def ivanov() -> SaveResearcherRequest:
        return SaveResearcherRequest("Иванов И.И.", "ИУ7")

    # --- сущности, «уже сохранённые» в хранилище (для ответов моков) ---
    @staticmethod
    def stored_forest_cat() -> Species:
        return Species(1, "Felis silvestris", "Лесной кот")

    @staticmethod
    def stored_observation_by_river() -> Observation:
        return Observation(10, date(2026, 3, 1), 7, 1, 2, 3, "у реки")

    @staticmethod
    def growing_population_records() -> list[PopulationRecord]:
        """Пять ежемесячных точек с ростом численности: достаточно для тренда."""
        return [
            PopulationRecord(date(2026, 4, 1), 12),
            PopulationRecord(date(2026, 5, 1), 15),
            PopulationRecord(date(2026, 6, 1), 18),
            PopulationRecord(date(2026, 7, 1), 20),
            PopulationRecord(date(2026, 8, 1), 22),
        ]
