"""Исключения компонента доступа к данным."""


class DataAccessError(Exception):
    """Сбой при работе с хранилищем."""


class DataValidationError(DataAccessError):
    """Данные не проходят проверки уровня хранилища."""


class EntityNotFoundError(DataAccessError):
    """Запись с указанным идентификатором отсутствует."""


class DuplicateEntityError(DataAccessError):
    """Нарушено ограничение уникальности."""


class IntegrityConstraintError(DataAccessError):
    """Нарушена ссылочная целостность или иное ограничение БД."""
