from dataclasses import dataclass, field

from domain.services.env import get_int_value, get_str_value


@dataclass(slots=True, frozen=True, kw_only=True)
class DatabaseConfig:
    POSTGRES_DRIVER: str = field(
        default_factory=lambda: get_str_value("POSTGRES_DRIVER", "postgresql+asyncpg")
    )
    POSTGRES_USER: str = field(default_factory=lambda: get_str_value("POSTGRES_USER", "postgres"))
    POSTGRES_PASSWORD: str = field(
        default_factory=lambda: get_str_value("POSTGRES_PASSWORD", "postgres")
    )
    POSTGRES_HOST: str = field(default_factory=lambda: get_str_value("POSTGRES_HOST", "localhost"))
    POSTGRES_PORT: int = field(default_factory=lambda: get_int_value("POSTGRES_PORT", 5432))
    POSTGRES_DATABASE: str = field(
        default_factory=lambda: get_str_value("POSTGRES_DATABASE", "postgres")
    )
