from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True, slots=True)
class Response[ResponseModel]:
    status: str = "data"
    message: str = "ok"
    data: ResponseModel | None = None
