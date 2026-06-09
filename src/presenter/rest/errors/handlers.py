import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from fastapi.exceptions import HTTPException as FastApiHTTPException

from domain.errors.codes import ErrorCode
from domain.errors.exceptions import AppException
from domain.utils.sentinel import unset
from presenter.rest.errors.models import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning(
        f"Бизнес-ошибка [{exc.error_code}] на {request.method} {request.url.path}: {exc.message}"
    )
    response = ErrorResponse(
        message=exc.error_code,
        error=ErrorDetail(message=exc.message, extra=exc.extra or unset),
    )
    return JSONResponse(status_code=exc.status_code, content=response.to_dict())


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
    request: Request, exc: FastApiHTTPException
) -> JSONResponse:
    logger.info(
        f"Стандартная HTTP ошибка {exc.status_code} на "
        f"{request.method} {request.url.path}: {exc.detail}"
    )
    code = _code_for_status(exc.status_code)
    response = ErrorResponse(message=code, error=ErrorDetail(message=str(exc.detail)))
    return JSONResponse(status_code=exc.status_code, content=response.to_dict())


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.info(f"Ошибка валидации запроса на {request.method} {request.url.path}")
    errors = [
        {"field": ".".join(str(x) for x in err["loc"] if x != "body"), "msg": err["msg"]}
        for err in exc.errors()
    ]
    response = ErrorResponse(
        message=ErrorCode.VALIDATION_ERROR,
        error=ErrorDetail(
            message="Ошибка валидации входящих данных",
            extra={"details": errors},
        ),
    )
    return JSONResponse(status_code=422, content=response.to_dict())


async def internal_validation_exception_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    logger.error(
        f"Внутренняя ошибка валидации Pydantic на {request.method} {request.url.path}: {exc}"
    )
    errors = [
        {"field": ".".join(str(x) for x in err["loc"]), "msg": err["msg"]} for err in exc.errors()
    ]
    response = ErrorResponse(
        message=ErrorCode.INTERNAL_SERVER_ERROR,
        error=ErrorDetail(
            message="Внутренняя ошибка сервера при обработке данных",
            extra={"details": errors} if logger.isEnabledFor(logging.DEBUG) else unset,
        ),
    )
    return JSONResponse(status_code=500, content=response.to_dict())


async def unknown_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Критическая ошибка (500) на {request.method} {request.url.path}: {exc}")
    response = ErrorResponse(
        message=ErrorCode.INTERNAL_SERVER_ERROR,
        error=ErrorDetail(message="Внутренняя ошибка сервера"),
    )
    return JSONResponse(status_code=500, content=response.to_dict())


ExceptionHandler = Callable[[Request, Any], Awaitable[JSONResponse]]

HANDLERS_MAP: tuple[tuple[type[Exception], ExceptionHandler], ...] = (
    (AppException, app_exception_handler),
    (FastApiHTTPException, fastapi_http_exception_handler),
    (RequestValidationError, request_validation_exception_handler),
    (PydanticValidationError, internal_validation_exception_handler),
    (Exception, unknown_exception_handler),
)
