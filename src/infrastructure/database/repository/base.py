from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    __slots__ = "_session"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
