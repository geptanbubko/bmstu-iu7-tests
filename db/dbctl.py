"""Управление тестовым хранилищем SQLite последовательным запуском SQL-скриптов.

    python db/dbctl.py init     --db PATH [--force]  # 01_schema.sql → 02_seed.sql
    python db/dbctl.py rollback --db PATH            # 90_rollback.sql → 02_seed.sql (одной транзакцией)
    python db/dbctl.py verify   --db PATH            # целостность + совпадение с эталоном из скриптов
    python db/dbctl.py fingerprint --db PATH         # отпечаток содержимого (sha256)

Модуль используется и integration-тестами, и контейнером стенда (docker/app.Dockerfile).
"""
from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent / "sql"
SCHEMA_SCRIPT = SQL_DIR / "01_schema.sql"
SEED_SCRIPT = SQL_DIR / "02_seed.sql"
ROLLBACK_SCRIPT = SQL_DIR / "90_rollback.sql"
TABLES = ("researchers", "species", "locations", "observations", "population_records")


class StorageIntegrityError(RuntimeError):
    """Хранилище повреждено или отличается от эталонного состояния."""


@dataclass(frozen=True)
class StorageState:
    fingerprint: str
    row_counts: dict[str, int]


def _read(script: Path) -> str:
    return script.read_text(encoding="utf-8")


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _run_in_transaction(db_path: Path, scripts: tuple[Path, ...]) -> None:
    body = "\n".join(_read(script) for script in scripts)
    conn = _connect(db_path)
    try:
        conn.executescript(f"BEGIN IMMEDIATE;\n{body}\nCOMMIT;")
    except sqlite3.Error:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def init(db_path: Path, force: bool = False) -> bool:
    """Создаёт хранилище из скриптов. False — файл уже был и force не задан."""
    db_path = Path(db_path)
    if db_path.exists():
        if not force:
            return False
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path)
    try:
        conn.executescript(_read(SCHEMA_SCRIPT))
    finally:
        conn.close()
    _run_in_transaction(db_path, (SEED_SCRIPT,))
    return True


def rollback(db_path: Path) -> None:
    """Возвращает данные к состоянию сразу после init (атомарно)."""
    _run_in_transaction(Path(db_path), (ROLLBACK_SCRIPT, SEED_SCRIPT))


def state(db_path: Path) -> StorageState:
    conn = _connect(Path(db_path))
    try:
        digest = hashlib.sha256()
        counts: dict[str, int] = {}
        for table in TABLES:
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
            counts[table] = len(rows)
            digest.update(table.encode())
            for row in rows:
                digest.update(repr(row).encode())
        sequences = conn.execute("SELECT name, seq FROM sqlite_sequence ORDER BY name").fetchall()
        digest.update(repr(sequences).encode())
        return StorageState(digest.hexdigest(), counts)
    finally:
        conn.close()


def reference_state() -> StorageState:
    """Эталон: состояние свежего хранилища, построенного теми же скриптами."""
    with tempfile.TemporaryDirectory(prefix="wildlife-ref-") as tmp:
        ref = Path(tmp) / "reference.db"
        init(ref)
        return state(ref)


def check_integrity(db_path: Path) -> None:
    conn = _connect(Path(db_path))
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise StorageIntegrityError(f"integrity_check: {result}")
        broken = conn.execute("PRAGMA foreign_key_check").fetchall()
        if broken:
            raise StorageIntegrityError(f"foreign_key_check: {broken}")
    finally:
        conn.close()


def verify(db_path: Path, expected: StorageState | None = None) -> StorageState:
    """Проверяет целостность и совпадение с эталоном; возвращает фактическое состояние."""
    check_integrity(db_path)
    actual = state(db_path)
    expected = expected or reference_state()
    if actual != expected:
        raise StorageIntegrityError(
            f"Состояние хранилища отличается от эталона: {actual.row_counts} != {expected.row_counts}"
        )
    return actual


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("init", "rollback", "verify", "fingerprint"))
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="init: пересоздать существующий файл")
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            created = init(args.db, force=args.force)
            print(f"[dbctl] init {args.db}: {'создано из скриптов' if created else 'уже существует'}")
        elif args.command == "rollback":
            rollback(args.db)
            print(f"[dbctl] rollback {args.db}: выполнены 90_rollback.sql + 02_seed.sql")
        elif args.command == "verify":
            actual = verify(args.db)
            print(f"[dbctl] verify {args.db}: OK {actual.row_counts}")
        else:
            current = state(args.db)
            print(f"{current.fingerprint} {current.row_counts}")
    except (StorageIntegrityError, sqlite3.Error) as exc:
        print(f"[dbctl] {args.command} {args.db}: ОШИБКА {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
