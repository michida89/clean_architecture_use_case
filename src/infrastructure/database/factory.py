import logging

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from infrastructure.database.config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseFactory:
    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def build_database_url(self) -> URL:
        return URL.create(
            drivername=self._config.POSTGRES_DRIVER,
            username=self._config.POSTGRES_USER,
            password=self._config.POSTGRES_PASSWORD,
            host=self._config.POSTGRES_HOST,
            port=self._config.POSTGRES_PORT,
            database=self._config.POSTGRES_DATABASE,
        )

    def create_engine(self) -> AsyncEngine:
        if self._engine is None:
            logger.info(
                "Creating database engine for %s:%s/%s",
                self._config.POSTGRES_HOST,
                self._config.POSTGRES_PORT,
                self._config.POSTGRES_DATABASE,
            )
            self._engine = create_async_engine(
                url=self.build_database_url(),
                echo=False,
                echo_pool=False,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,
                connect_args={
                    "timeout": 10,
                    "command_timeout": 60,
                    "server_settings": {
                        "application_name": "project",
                        "jit": "off",
                    },
                },
            )
        return self._engine

    def create_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.create_engine(),
                expire_on_commit=False,
            )
        return self._session_factory

    async def dispose(self) -> None:
        if self._engine is not None:
            logger.info("Disposing database engine")
            await self._engine.dispose()
            self._engine = None
