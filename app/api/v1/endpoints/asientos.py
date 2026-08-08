from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db, requiere_escritura
from app.models.asiento import Asiento
from app.models.usuario import Usuario
from app.schemas.asiento import AsientoCreate, AsientoListResponse, AsientoRead

router = APIRouter(prefix="/asientos", tags=["Asientos contables"])


def _obtener_o_404(db: Session, asiento_id: int) -> Asiento:
    asiento = crud.asiento.get(db, asiento_id)
    if asiento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asiento no encontrado")
    return asiento


@router.post("/", response_model=AsientoRead, status_code=status.HTTP_201_CREATED)
def crear_asiento(
    asiento_in: AsientoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_escritura),
) -> Asiento:
    try:
        return crud.asiento.create(db, obj_in=asiento_in, usuario=usuario)
    except crud.asiento.CuentaInvalidaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/", response_model=AsientoListResponse)
def listar_asientos(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=500),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    cuenta_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_desde no puede ser posterior a fecha_hasta",
        )
    filtros = {"fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta, "cuenta_id": cuenta_id}
    items = crud.asiento.get_multi(db, skip=skip, limit=limit, **filtros)
    total = crud.asiento.count(db, **filtros)
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/{asiento_id}", response_model=AsientoRead)
def obtener_asiento(asiento_id: int, db: Session = Depends(get_db)) -> Asiento:
    return _obtener_o_404(db, asiento_id)


@router.post(
    "/{asiento_id}/reversar", response_model=AsientoRead, status_code=status.HTTP_201_CREATED
)
def reversar_asiento(
    asiento_id: int,
    fecha: date | None = Query(
        default=None, description="Fecha del asiento de reversión; por defecto, hoy"
    ),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_escritura),
) -> Asiento:
    original = _obtener_o_404(db, asiento_id)
    try:
        return crud.asiento.reversar(db, original=original, fecha=fecha, usuario=usuario)
    except crud.asiento.AsientoYaReversadoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except crud.asiento.CuentaInvalidaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{asiento_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asiento(
    asiento_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_escritura),
) -> None:
    asiento = _obtener_o_404(db, asiento_id)
    try:
        crud.asiento.remove(db, db_obj=asiento)
    except crud.asiento.AsientoReversadoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
