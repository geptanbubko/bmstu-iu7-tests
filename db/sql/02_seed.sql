-- 02. Заведение тестовых данных. Идентификаторы заданы явно: состояние одинаково при каждом запуске.
PRAGMA foreign_keys = ON;

INSERT INTO researchers (id, full_name, organization) VALUES
    (1, 'Смирнова А.А.', 'Заповедник «Кивач»'),
    (2, 'Орлов Д.С.', 'ИУ7');

INSERT INTO species (id, scientific_name, common_name, conservation_status) VALUES
    (1, 'Alces alces', 'Лось', 'LC'),
    (2, 'Lynx lynx', 'Рысь', 'LC'),
    (3, 'Gulo gulo', 'Росомаха', 'VU');

INSERT INTO locations (id, name, region, habitat_type) VALUES
    (1, 'Кивач', 'Карелия', 'тайга'),
    (2, 'Лапландия', 'Мурманская область', 'тундра');

-- Лось в Киваче: пять ежемесячных учётов — достаточно для тренда.
INSERT INTO observations (id, observation_date, individuals_count, notes, species_id, location_id, researcher_id) VALUES
    (1, '2025-04-15', 11, 'seed', 1, 1, 1),
    (2, '2025-05-15', 13, 'seed', 1, 1, 1),
    (3, '2025-06-15', 14, 'seed', 1, 1, 1),
    (4, '2025-07-15', 16, 'seed', 1, 1, 1),
    (5, '2025-08-15', 19, 'seed', 1, 1, 1),
    (6, '2025-06-01', 2, 'seed', 2, 2, 2),
    (7, '2025-07-01', 3, 'seed', 2, 2, 2);

INSERT INTO population_records (id, record_date, population_size, method, species_id, location_id, researcher_id) VALUES
    (1, '2025-04-15', 11, 'observation', 1, 1, 1),
    (2, '2025-05-15', 13, 'observation', 1, 1, 1),
    (3, '2025-06-15', 14, 'observation', 1, 1, 1),
    (4, '2025-07-15', 16, 'observation', 1, 1, 1),
    (5, '2025-08-15', 19, 'observation', 1, 1, 1),
    -- Рысь в Лапландии: две точки — тренд не строится.
    (6, '2025-06-01', 2, 'observation', 2, 2, 2),
    (7, '2025-07-01', 3, 'observation', 2, 2, 2);
