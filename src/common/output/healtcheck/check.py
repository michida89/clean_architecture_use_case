from dataclasses import dataclass


@dataclass(kw_only=True, frozen=True, slots=True)
class HealthCheckOutputDto:
    ok: bool
