from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db, requiere_escritura
from app.models.cuenta import Cuenta
from app.models.usuario import Usuario
from app.schemas.cuenta import CuentaCreate, CuentaRead, CuentaTree, CuentaUpdate

router = APIRouter(prefix="/cuentas", tags=["Plan de cuentas"])


def _obtener_o_404(db: Session, cuenta_id: int) -> Cuenta:
    cuenta = crud.cuenta.get(db, cuenta_id)
    if cuenta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    return cuenta


@router.post("/", response_model=CuentaRead, status_code=status.HTTP_201_CREATED)
def crear_cuenta(
    cuenta_in: CuentaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_escritura),
) -> Cuenta:
    try:
        return crud.cuenta.create(db, obj_in=cuenta_in)
    except crud.cuenta.CuentaNoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una cuenta con el código '{cuenta_in.codigo}'",
        ) from exc


@router.get("/", response_model=list[CuentaRead])
def listar_cuentas(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
) -> list[Cuenta]:
    return crud.cuenta.get_multi(db, skip=skip, limit=limit)


@router.get("/arbol", response_model=list[CuentaTree])
def obtener_arbol_cuentas(db: Session = Depends(get_db)) -> list[Cuenta]:
    return crud.cuenta.get_tree(db)


@router.get("/{cuenta_id}", response_model=CuentaRead)
def obtener_cuenta(cuenta_id: int, db: Session = Depends(get_db)) -> Cuenta:
    return _obtener_o_404(db, cuenta_id)


@router.patch("/{cuenta_id}", response_model=CuentaRead)
def actualizar_cuenta(
    cuenta_id: int,
    cuenta_in: CuentaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_escritura),
) -> Cuenta:
    cuenta = _obtener_o_404(db, cuenta_id)
    try:
        return crud.cuenta.update(db, db_obj=cuenta, obj_in=cuenta_in)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflicto al actualizar la cuenta (código duplicado)",
        ) from exc


@router.delete("/{cuenta_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cuenta(
    cuenta_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_escritura),
) -> None:
    cuenta = _obtener_o_404(db, cuenta_id)
    try:
        crud.cuenta.remove(db, db_obj=cuenta)
    except (crud.cuenta.CuentaConHijasError, crud.cuenta.CuentaConMovimientosError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar la cuenta por una restricción de integridad",
        ) from exc
