from typing import Any

from domain.errors.codes import ErrorCode
from domain.errors.models import ErrorDetailModel, ErrorResponseModel


class AppException(Exception):
    status_code: int = 400
    error_code: ErrorCode = ErrorCode.BAD_REQUEST
    message: str = "Некорректный запрос"

    def __init__(self, message: str | None = None, extra: dict[str, Any] | None = None):
        self.message = message or self.message
        self.extra = extra or {}

        self.response_data = ErrorResponseModel(
            error=ErrorDetailModel(code=self.error_code, message=self.message, extra=self.extra)
        )
