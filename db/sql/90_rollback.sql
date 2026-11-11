-- 90. Откат: удаление всех данных и сброс счётчиков AUTOINCREMENT.
-- После этого скрипта снова выполняется 02_seed.sql — хранилище возвращается к исходному состоянию.
PRAGMA foreign_keys = ON;

DELETE FROM population_records;
DELETE FROM observations;
DELETE FROM species;
DELETE FROM locations;
DELETE FROM researchers;
DELETE FROM sqlite_sequence;
