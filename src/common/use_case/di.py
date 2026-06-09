from dishka import Provider, Scope, provide

from common.use_case.query.healthcheck.check import HealthCheckQuery


class UseCaseProvider(Provider):
    health_check = provide(HealthCheckQuery, scope=Scope.REQUEST)
