from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import config
from domain.repository.healtcheck import IHealthCheckRepository
from domain.uow import AbstractUow
from infrastructure.database.config import DatabaseConfig
from infrastructure.database.factory import DatabaseFactory
from infrastructure.database.repository.healtcheck import HealthCheckRepository
from infrastructure.database.uow import SqlalchemyUow


class DatabaseProvider(Provider):
    def __init__(self, db_config: DatabaseConfig | None = None) -> None:
        super().__init__()
        self._config = db_config or config.database

    @provide(scope=Scope.APP)
    async def get_factory(self) -> AsyncIterable[DatabaseFactory]:
        factory = DatabaseFactory(self._config)
        yield factory
        await factory.dispose()

    @provide(scope=Scope.APP)
    def get_session_factory(self, factory: DatabaseFactory) -> async_sessionmaker[AsyncSession]:
        return factory.create_session_factory()

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        async with session_factory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def get_uow(self, session: AsyncSession) -> AbstractUow:
        return SqlalchemyUow(session)

    @provide(scope=Scope.REQUEST)
    def get_healthcheck_repository(self, session: AsyncSession) -> IHealthCheckRepository:
        return HealthCheckRepository(session)
