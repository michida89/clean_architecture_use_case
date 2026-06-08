from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from domain.repository.healtcheck import IHealthCheckRepository
from infrastructure.database.repository.base import BaseRepository


class HealthCheckRepository(IHealthCheckRepository, BaseRepository):
    async def check(self) -> bool:
        try:
            await self._session.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError):
            return False
        return True
