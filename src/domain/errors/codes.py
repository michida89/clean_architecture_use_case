from enum import StrEnum


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    INTERNAL_SERVER_ERROR = "internal_server_error"
    NOT_FOUND = "not_found"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
