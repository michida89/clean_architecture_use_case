from dataclasses import dataclass, field
from typing import Final

from common.config import ApplicationConfig
from infrastructure.auth.config import AuthConfig
from infrastructure.database.config import DatabaseConfig

@dataclass(frozen=True, kw_only=True, slots=True)
class Config:
    application: ApplicationConfig = field(default_factory=ApplicationConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)

config: Final[Config] = Config()
