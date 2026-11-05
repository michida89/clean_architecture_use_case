import os
from collections.abc import Callable

from domain.utils.sentinel import Unset, unset


class MissingEnvVar(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Required environment variable '{key}' is not set")


def _get[T](key: str, default: Unset | T, caster: Callable[[str], T]) -> T:
    value = os.environ.get(key)
    if value is None:
        if isinstance(default, Unset):
            raise MissingEnvVar(key)
        return default
    return caster(value)


def _to_bool(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes", "y", "on")


def get_str_value(key: str, default: Unset | str = unset) -> str:
    return _get(key, default, str)


def get_int_value(key: str, default: Unset | int = unset) -> int:
    return _get(key, default, int)


def get_float_value(key: str, default: Unset | float = unset) -> float:
    return _get(key, default, float)


def get_bool_value(key: str, default: Unset | bool = unset) -> bool:
    return _get(key, default, _to_bool)
