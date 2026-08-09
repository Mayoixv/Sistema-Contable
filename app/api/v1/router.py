from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.endpoints import (
    asientos,
    auth,
    balance_comprobacion,
    balance_general,
    cierres,
    cuentas,
    estado_resultados,
    libro_mayor,
    usuarios,
)

api_router = APIRouter()
api_router.include_router(auth.router)

# El resto de la API contiene datos contables: todo requiere sesión iniciada.
_requiere_login = [Depends(get_current_user)]
api_router.include_router(cuentas.router, dependencies=_requiere_login)
api_router.include_router(asientos.router, dependencies=_requiere_login)
api_router.include_router(libro_mayor.router, dependencies=_requiere_login)
api_router.include_router(balance_comprobacion.router, dependencies=_requiere_login)
api_router.include_router(estado_resultados.router, dependencies=_requiere_login)
api_router.include_router(balance_general.router, dependencies=_requiere_login)
api_router.include_router(cierres.router, dependencies=_requiere_login)
api_router.include_router(usuarios.router, dependencies=_requiere_login)
