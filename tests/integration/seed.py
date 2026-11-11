"""Идентификаторы и факты из db/sql/02_seed.sql, на которые опираются integration-тесты."""
from datetime import date

MOOSE_ID = 1          # Alces alces — пять учётов в Киваче, тренд строится
LYNX_ID = 2           # Lynx lynx — два учёта в Лапландии, тренда нет
WOLVERINE_ID = 3      # Gulo gulo — без наблюдений
KIVACH_ID = 1
LAPLAND_ID = 2
SMIRNOVA_ID = 1
ORLOV_ID = 2

SPECIES_COUNT = 3
OBSERVATIONS_COUNT = 7
YEAR_2025 = (date(2025, 1, 1), date(2025, 12, 31))
