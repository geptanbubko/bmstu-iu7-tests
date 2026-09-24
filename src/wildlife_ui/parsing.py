"""Разбор ввода консоли. Ошибки формата — ValidationError бизнес-слоя."""
from datetime import date, datetime

from wildlife_business.exceptions import ValidationError


def parse_int(raw: str, field: str) -> int:
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValidationError(f"{field}: введите целое число") from exc


def parse_optional_int(raw: str, field: str) -> int | None:
    value = raw.strip()
    if not value:
        return None
    return parse_int(value, field)


def parse_date(raw: str, field: str) -> date:
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError(f"{field}: дата в формате ГГГГ-ММ-ДД") from exc


def parse_optional_text(raw: str) -> str | None:
    value = raw.strip()
    return value or None
