#!/bin/sh
# Старт стенда: хранилище поднимается скриптами db/sql/*.sql и проверяется до запуска приложения.
set -eu
DB=/data/wildlife.db

python db/dbctl.py init --db "$DB"
if ! python db/dbctl.py verify --db "$DB"; then
    echo "[stand] хранилище отличается от эталона — принудительный откат"
    python db/dbctl.py rollback --db "$DB"
    python db/dbctl.py verify --db "$DB"
fi

exec python -m wildlife_app --ui gui --config /app/config.ini
