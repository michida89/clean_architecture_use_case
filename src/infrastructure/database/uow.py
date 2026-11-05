from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from domain.uow import AbstractUow


class SqlalchemyUow(AbstractUow):
    session: AsyncSession
    transaction: AsyncSessionTransaction | None

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transaction: AsyncSessionTransaction | None = None

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def create_transaction(self) -> None:
        if not self.session.in_transaction() and self.session.is_active:
            self.transaction = await self.session.begin()

    async def close_transaction(self) -> None:
        if self.session.is_active:
            await self.session.close()
