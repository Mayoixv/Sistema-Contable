from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db, requiere_admin
from app.models.cierre import Cierre
from app.models.usuario import Usuario
from app.schemas.cierre import CierreCreate, CierreRead

router = APIRouter(prefix="/cierres", tags=["Cierre de ejercicio"])


@router.post(
    "/",
    response_model=CierreRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cerrar el ejercicio (solo admin)",
    description=(
        "Genera el asiento que salda las cuentas de ingreso, costo y gasto "
        "contra la cuenta de patrimonio indicada. Es una operación que "
        "reescribe la lectura de todo un período, por eso queda restringida "
        "a un admin."
    ),
)
def crear_cierre(
    cierre_in: CierreCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_admin),
) -> Cierre:
    try:
        return crud.cierre.crear(
            db,
            fecha_cierre=cierre_in.fecha_cierre,
            cuenta_resultado_id=cierre_in.cuenta_resultado_id,
            usuario=usuario,
        )
    except crud.cierre.CuentaResultadoInvalidaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except crud.cierre.SinResultadoParaCerrarError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except crud.cierre.PeriodoYaCerradoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/", response_model=list[CierreRead])
def listar_cierres(db: Session = Depends(get_db)) -> list[Cierre]:
    return crud.cierre.get_multi(db)
