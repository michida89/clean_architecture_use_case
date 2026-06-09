from dataclasses import dataclass, fields, is_dataclass
from typing import Any

from domain.errors.codes import ErrorCode
from domain.utils.sentinel import Unset, unset


@dataclass(slots=True, frozen=True, kw_only=True)
class ErrorDetail:
    message: str
    extra: dict[str, Any] | Unset = unset


@dataclass(slots=True, frozen=True, kw_only=True)
class ErrorResponse:
    status: str = "error"
    message: ErrorCode = ErrorCode.UNKNOWN_ERROR
    error: ErrorDetail | Unset = unset

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)


def _to_dict(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        result: dict[str, Any] = {}
        for f in fields(value):
            field_value = getattr(value, f.name)
            if isinstance(field_value, Unset):
                continue
            result[f.name] = _to_dict(field_value)
        return result
    if isinstance(value, (list, tuple)):
        return [_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_dict(item) for key, item in value.items()}
    if isinstance(value, ErrorCode):
        return value.value
    return value
