import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiomisc.service.uvicorn import UvicornService
from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI

from common.use_case.di import UseCaseProvider
from config import Config
from infrastructure.database.di import DatabaseProvider
from presenter.rest.errors.handlers import HANDLERS_MAP
from presenter.rest.middleware import include_cors_middleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.dishka_container.close()


class ApplicationFactory(UvicornService):
    def __init__(self, config: Config, router: APIRouter, **kwargs) -> None:
        self.config = config
        self.router = router
        super().__init__(
            host=config.application.APP_HOST,
            port=config.application.APP_PORT,
            **kwargs,
        )

    async def create_application(self) -> FastAPI:
        logger.info(
            "Starting %s v%s",
            self.config.application.APP_TITLE,
            self.config.application.APP_VERSION,
        )
        app = FastAPI(
            description=self.config.application.APP_DESCRIPTION,
            version=self.config.application.APP_VERSION,
            title=self.config.application.APP_TITLE,
            docs_url=self.config.application.APP_DOCS_URL,
            redoc_url=self.config.application.APP_REDOC_URL,
            debug=self.config.application.APP_DEBUG,
            lifespan=_lifespan,
        )

        self._include_router(app=app)
        self._include_middleware(app=app)
        self._include_exception_handlers(app=app)
        self._setup_di(app=app)

        logger.info(
            "Application listening on %s:%s",
            self.config.application.APP_HOST,
            self.config.application.APP_PORT,
        )
        return app

    def _setup_di(self, app: FastAPI) -> None:
        container = make_async_container(
            DatabaseProvider(self.config.database),
            UseCaseProvider(),
        )
        setup_dishka(container, app)

    def _include_router(self, app: FastAPI) -> None:
        app.include_router(self.router)

    def _include_middleware(self, app: FastAPI) -> None:
        include_cors_middleware(app=app)

    def _include_exception_handlers(self, app: FastAPI) -> None:
        for exception, handler in HANDLERS_MAP:
            app.add_exception_handler(exception, handler)
