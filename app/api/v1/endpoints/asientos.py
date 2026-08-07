from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db
from app.models.asiento import Asiento
from app.schemas.asiento import AsientoCreate, AsientoRead

router = APIRouter(prefix="/asientos", tags=["Asientos contables"])


def _obtener_o_404(db: Session, asiento_id: int) -> Asiento:
    asiento = crud.asiento.get(db, asiento_id)
    if asiento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asiento no encontrado")
    return asiento


@router.post("/", response_model=AsientoRead, status_code=status.HTTP_201_CREATED)
def crear_asiento(asiento_in: AsientoCreate, db: Session = Depends(get_db)) -> Asiento:
    try:
        return crud.asiento.create(db, obj_in=asiento_in)
    except crud.asiento.CuentaInvalidaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/", response_model=list[AsientoRead])
def listar_asientos(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
) -> list[Asiento]:
    return crud.asiento.get_multi(db, skip=skip, limit=limit)


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
) -> Asiento:
    original = _obtener_o_404(db, asiento_id)
    try:
        return crud.asiento.reversar(db, original=original, fecha=fecha)
    except crud.asiento.AsientoYaReversadoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except crud.asiento.CuentaInvalidaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{asiento_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asiento(asiento_id: int, db: Session = Depends(get_db)) -> None:
    asiento = _obtener_o_404(db, asiento_id)
    try:
        crud.asiento.remove(db, db_obj=asiento)
    except crud.asiento.AsientoReversadoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
