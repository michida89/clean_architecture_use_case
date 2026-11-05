from abc import abstractmethod
from typing import Protocol


class IHealthCheckRepository(Protocol):
    @abstractmethod
    async def check(self) -> bool: ...
