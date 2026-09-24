"""Исключения компонента бизнес-логики."""


class BusinessError(Exception):
    """Базовое исключение домена."""


class ValidationError(BusinessError):
    """Некорректные входные данные."""


class DuplicateSpeciesError(BusinessError):
    """Вид с таким научным названием уже есть."""


class NoDataError(BusinessError):
    """Нет записей за выбранный период."""


class NotFoundError(BusinessError):
    """Сущность не найдена."""
