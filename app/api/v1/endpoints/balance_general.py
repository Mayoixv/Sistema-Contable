from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db
from app.schemas.balance_general import BalanceGeneralResponse
from app.utils.csv_export import csv_response, filas_a_csv

router = APIRouter(prefix="/balance-general", tags=["Balance general"])

_CSV_COLUMNAS = ["seccion", "codigo", "nombre", "saldo"]


def _a_csv(reporte: dict) -> str:
    filas: list[dict] = []
    for seccion, clave in (
        ("activo", "activos"),
        ("pasivo", "pasivos"),
        ("patrimonio", "patrimonio"),
    ):
        for fila in reporte[clave]:
            filas.append({"seccion": seccion, **fila})
    filas.append(
        {
            "seccion": "patrimonio",
            "codigo": "",
            "nombre": "Resultado acumulado",
            "saldo": reporte["resultado_acumulado"],
        }
    )
    for etiqueta, clave in (
        ("TOTAL ACTIVO", "total_activo"),
        ("TOTAL PASIVO", "total_pasivo"),
        ("TOTAL PATRIMONIO", "total_patrimonio"),
        ("TOTAL PASIVO + PATRIMONIO", "total_pasivo_mas_patrimonio"),
    ):
        filas.append({"seccion": "", "codigo": "", "nombre": etiqueta, "saldo": reporte[clave]})
    return filas_a_csv(_CSV_COLUMNAS, filas)


@router.get("/", response_model=None)
def obtener_balance_general(
    fecha_corte: date | None = Query(
        default=None, description="Por defecto, todo el historial hasta hoy"
    ),
    formato: Literal["json", "csv"] = Query(default="json"),
    db: Session = Depends(get_db),
) -> BalanceGeneralResponse | Response:
    reporte = crud.balance_general.get_balance_general(db, fecha_corte=fecha_corte)
    if formato == "csv":
        return csv_response(_a_csv(reporte), nombre_archivo="balance_general.csv")
    return BalanceGeneralResponse.model_validate(reporte)
