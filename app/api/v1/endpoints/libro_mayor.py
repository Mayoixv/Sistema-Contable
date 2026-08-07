from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db
from app.schemas.libro_mayor import LibroMayorResponse

router = APIRouter(prefix="/libro-mayor", tags=["Libro mayor"])


@router.get("/{cuenta_id}", response_model=LibroMayorResponse)
def obtener_libro_mayor(
    cuenta_id: int,
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    cuenta = crud.cuenta.get(db, cuenta_id)
    if cuenta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_desde no puede ser posterior a fecha_hasta",
        )
    return crud.libro_mayor.get_libro_mayor(
        db, cuenta=cuenta, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )
