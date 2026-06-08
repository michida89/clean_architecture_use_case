from fastapi import APIRouter

from presenter.rest.api.v1.router import router as v1_router
from presenter.rest.api.healcheck.check import router as healthcheck_router 

router = APIRouter(prefix="/api")

router.include_router(v1_router)

router.include_router(healthcheck_router)
