from dataclasses import dataclass, field

from domain.services.env import get_bool_value, get_int_value, get_str_value


@dataclass(frozen=True, kw_only=True, slots=True)
class ApplicationConfig:
    APP_HOST: str = field(default_factory=lambda: get_str_value("APP_HOST", "0.0.0.0"))
    APP_PORT: int = field(default_factory=lambda: get_int_value("APP_PORT", 8000))
    APP_TITLE: str = field(default_factory=lambda: get_str_value("APP_TITLE", "My Awesome API"))
    APP_DESCRIPTION: str = field(
        default_factory=lambda: get_str_value("APP_DESCRIPTION", "This is a project description")
    )
    APP_VERSION: str = field(default_factory=lambda: get_str_value("APP_VERSION", "1.0.0"))
    APP_DEBUG: bool = field(default_factory=lambda: get_bool_value("APP_DEBUG", True))
    APP_DOCS_URL: str = field(default_factory=lambda: get_str_value("APP_DOCS_URL", "/docs"))
    APP_REDOC_URL: str = field(default_factory=lambda: get_str_value("APP_REDOC_URL", "/redoc"))
