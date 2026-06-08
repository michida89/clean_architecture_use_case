import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from domain.errors.codes import ErrorCode
from domain.errors.exceptions import AppException
from domain.errors.models import ErrorDetailModel, ErrorResponseModel

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning(
        f"Бизнес-ошибка [{exc.error_code}] на {request.method} {request.url.path}: {exc.message}"
    )
    return JSONResponse(status_code=exc.status_code, content=exc.response_data.model_dump())


_HTTP_STATUS_TO_CODE = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    422: ErrorCode.VALIDATION_ERROR,
}


def _code_for_status(status_code: int) -> ErrorCode:
    if status_code >= 500:
        return ErrorCode.INTERNAL_SERVER_ERROR
    return _HTTP_STATUS_TO_CODE.get(status_code, ErrorCode.BAD_REQUEST)


async def fastapi_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    logger.info(
        f"Стандартная HTTP ошибка {exc.status_code} на "
        f"{request.method} {request.url.path}: {exc.detail}"
    )
    code = _code_for_status(exc.status_code)
    response = ErrorResponseModel(error=ErrorDetailModel(code=code, message=str(exc.detail)))
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.info(f"Ошибка валидации запроса на {request.method} {request.url.path}")
    errors = [
        {"field": ".".join(str(x) for x in err["loc"] if x != "body"), "msg": err["msg"]}
        for err in exc.errors()
    ]
    response = ErrorResponseModel(
        error=ErrorDetailModel(
            code=ErrorCode.VALIDATION_ERROR,
            message="Ошибка валидации входящих данных",
            extra={"details": errors},
        )
    )
    return JSONResponse(status_code=422, content=response.model_dump())


async def internal_validation_exception_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    logger.error(
        f"Внутренняя ошибка валидации Pydantic на {request.method} {request.url.path}: {exc}"
    )
    errors = [
        {"field": ".".join(str(x) for x in err["loc"]), "msg": err["msg"]} for err in exc.errors()
    ]
    response = ErrorResponseModel(
        error=ErrorDetailModel(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="Внутренняя ошибка сервера при обработке данных",
            extra={"details": errors} if logger.isEnabledFor(logging.DEBUG) else None,
        )
    )
    return JSONResponse(status_code=500, content=response.model_dump())


async def unknown_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Критическая ошибка (500) на {request.method} {request.url.path}: {exc}")
    response = ErrorResponseModel(
        error=ErrorDetailModel(
            code=ErrorCode.INTERNAL_SERVER_ERROR, message="Внутренняя ошибка сервера"
        )
    )
    return JSONResponse(status_code=500, content=response.model_dump())


# `Any` for exc: each handler narrows it to its own type (Callable params are contravariant).
ExceptionHandler = Callable[[Request, Any], Awaitable[JSONResponse]]

HANDLERS_MAP: tuple[tuple[type[Exception], ExceptionHandler], ...] = (
    (AppException, app_exception_handler),
    (StarletteHTTPException, fastapi_http_exception_handler),
    (RequestValidationError, request_validation_exception_handler),
    (PydanticValidationError, internal_validation_exception_handler),
    (Exception, unknown_exception_handler),
)
