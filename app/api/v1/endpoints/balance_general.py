from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db
from app.schemas.balance_general import BalanceGeneralResponse

router = APIRouter(prefix="/balance-general", tags=["Balance general"])


@router.get("/", response_model=BalanceGeneralResponse)
def obtener_balance_general(
    fecha_corte: date | None = Query(
        default=None, description="Por defecto, todo el historial hasta hoy"
    ),
    db: Session = Depends(get_db),
) -> dict:
    return crud.balance_general.get_balance_general(db, fecha_corte=fecha_corte)
