from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db
from app.schemas.balance_comprobacion import BalanceComprobacionResponse
from app.utils.csv_export import csv_response, filas_a_csv

router = APIRouter(prefix="/balance-comprobacion", tags=["Balance de comprobación"])

_CSV_COLUMNAS = ["codigo", "nombre", "naturaleza", "saldo_inicial", "debito", "credito", "saldo_final"]


def _a_csv(reporte: dict) -> str:
    filas = list(reporte["cuentas"])
    filas.append(
        {
            "codigo": "",
            "nombre": "TOTAL",
            "naturaleza": "",
            "saldo_inicial": "",
            "debito": reporte["total_debitos"],
            "credito": reporte["total_creditos"],
            "saldo_final": "",
        }
    )
    return filas_a_csv(_CSV_COLUMNAS, filas)


@router.get("/", response_model=None)
def obtener_balance_comprobacion(
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    formato: Literal["json", "csv"] = Query(default="json"),
    db: Session = Depends(get_db),
) -> BalanceComprobacionResponse | Response:
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_desde no puede ser posterior a fecha_hasta",
        )
    reporte = crud.balance_comprobacion.get_balance_comprobacion(
        db, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )
    if formato == "csv":
        return csv_response(_a_csv(reporte), nombre_archivo="balance_comprobacion.csv")
    return BalanceComprobacionResponse.model_validate(reporte)
