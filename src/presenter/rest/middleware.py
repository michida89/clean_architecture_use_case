from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def include_cors_middleware(
    app: FastAPI,
    allow_origins: list[str] | None = None,
    allow_methods: list[str] | None = None,
    allow_headers: list[str] | None = None,
    allow_credentials: bool = False,
) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_methods=allow_methods or ["*"],
        allow_headers=allow_headers or ["*"],
        allow_credentials=allow_credentials,
    )
