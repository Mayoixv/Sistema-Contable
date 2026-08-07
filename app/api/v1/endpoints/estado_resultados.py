from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db
from app.schemas.estado_resultados import EstadoResultadosResponse

router = APIRouter(prefix="/estado-resultados", tags=["Estado de resultados"])


@router.get("/", response_model=EstadoResultadosResponse)
def obtener_estado_resultados(
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_desde no puede ser posterior a fecha_hasta",
        )
    return crud.estado_resultados.get_estado_resultados(
        db, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )
