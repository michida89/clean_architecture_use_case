from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True, slots=True)
class Response[ReponseModel]:
    status: str = "data"
    message: str = "ok"
    data: ReponseModel | dict | list | None = None
