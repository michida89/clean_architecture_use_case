from typing import Any

from pydantic import BaseModel

from domain.errors.codes import ErrorCode


class ErrorDetailModel(BaseModel):
    code: ErrorCode
    message: str
    extra: dict[str, Any] | None = None


class ErrorResponseModel(BaseModel):
    status: str = "error"
    error: ErrorDetailModel
