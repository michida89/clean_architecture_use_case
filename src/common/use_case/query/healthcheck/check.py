from common.use_case.base import IQuery
from domain.repository.healtcheck import IHealthCheckRepository


class HealthCheckQuery(IQuery[None, bool]):
    def __init__(self, repository: IHealthCheckRepository) -> None:
        self._repository = repository

    async def execute(self, *, input_dto: None) -> bool:
        return await self._repository.check()
