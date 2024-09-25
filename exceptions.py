class VariableMissingException(Exception):
    """Ошибка отсутствия переменной окружения."""

    pass


class RequestErrorException(Exception):
    """Ошибка запроса: код, отличный от 200."""

    pass


class RequestException(Exception):
    """Ошибка запроса."""

    pass
