from dataclasses import dataclass, field

from common.services.env import get_int_value, get_str_value


@dataclass(frozen=True, kw_only=True, slots=True)
class AuthConfig:
    JWT_ALGORITHM: str = field(default_factory=lambda: get_str_value("JWT_ALGORITHM", "RS256"))
    JWT_PRIVATE_KEY_PATH: str = field(
        default_factory=lambda: get_str_value("JWT_PRIVATE_KEY_PATH", "keys/jwt-private.pem")
    )
    JWT_PUBLIC_KEY_PATH: str = field(
        default_factory=lambda: get_str_value("JWT_PUBLIC_KEY_PATH", "keys/jwt-public.pem")
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = field(
        default_factory=lambda: get_int_value("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = field(
        default_factory=lambda: get_int_value("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7)
    )
