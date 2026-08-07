from fastapi import APIRouter

from app.api.v1.endpoints import (
    asientos,
    balance_comprobacion,
    balance_general,
    cuentas,
    estado_resultados,
    libro_mayor,
)

api_router = APIRouter()
api_router.include_router(cuentas.router)
api_router.include_router(asientos.router)
api_router.include_router(libro_mayor.router)
api_router.include_router(balance_comprobacion.router)
api_router.include_router(estado_resultados.router)
api_router.include_router(balance_general.router)
