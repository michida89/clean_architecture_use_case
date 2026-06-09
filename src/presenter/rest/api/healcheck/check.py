from fastapi import APIRouter
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from common.output.healtcheck.check import HealthCheckOutputDto
from common.use_case.query.healthcheck.check import HealthCheckQuery
from presenter.rest.api.response import Response


router = APIRouter(prefix="/healthcheck", tags=["HealthCheck"])


@router.get("", response_model=Response[HealthCheckOutputDto])
@inject
async def health_check(use_case: FromDishka[HealthCheckQuery]) -> HealthCheckOutputDto:
    return Response(
        status="data",
        message="server ok",
        data=HealthCheckOutputDto(ok=await use_case.execute(input_dto=None))
    )
    