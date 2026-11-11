-- 01. Генерация таблиц тестового хранилища (совпадает с wildlife_data/schema.py).
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS researchers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    organization TEXT,
    contact_info TEXT
);

CREATE TABLE IF NOT EXISTS species (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scientific_name TEXT NOT NULL UNIQUE,
    common_name TEXT NOT NULL,
    conservation_status TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    region TEXT,
    habitat_type TEXT,
    latitude REAL,
    longitude REAL
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_date TEXT NOT NULL,
    individuals_count INTEGER NOT NULL,
    notes TEXT,
    species_id INTEGER NOT NULL REFERENCES species(id),
    location_id INTEGER NOT NULL REFERENCES locations(id),
    researcher_id INTEGER NOT NULL REFERENCES researchers(id)
);

CREATE TABLE IF NOT EXISTS population_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_date TEXT NOT NULL,
    population_size INTEGER NOT NULL,
    method TEXT,
    notes TEXT,
    species_id INTEGER NOT NULL REFERENCES species(id),
    location_id INTEGER NOT NULL REFERENCES locations(id),
    researcher_id INTEGER NOT NULL REFERENCES researchers(id),
    UNIQUE (species_id, location_id, record_date)
);
