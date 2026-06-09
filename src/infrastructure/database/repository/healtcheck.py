import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from domain.repository.healtcheck import IHealthCheckRepository
from infrastructure.database.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class HealthCheckRepository(IHealthCheckRepository, BaseRepository):
    async def check(self) -> bool:
        try:
            await self._session.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError) as exc:
            logger.warning("Database health check failed: %s", exc)
            return False
        return True
