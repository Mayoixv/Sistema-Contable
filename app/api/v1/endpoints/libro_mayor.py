from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db
from app.schemas.libro_mayor import LibroMayorResponse
from app.utils.csv_export import csv_response, filas_a_csv

router = APIRouter(prefix="/libro-mayor", tags=["Libro mayor"])

_CSV_COLUMNAS = ["fecha", "asiento_numero", "descripcion", "debito", "credito", "saldo"]


def _a_csv(reporte: dict) -> str:
    filas = [
        {
            "fecha": reporte["fecha_desde"] or "",
            "asiento_numero": "",
            "descripcion": "Saldo inicial",
            "debito": "",
            "credito": "",
            "saldo": reporte["saldo_inicial"],
        },
        *reporte["movimientos"],
        {
            "fecha": "",
            "asiento_numero": "",
            "descripcion": "TOTAL",
            "debito": reporte["total_debitos"],
            "credito": reporte["total_creditos"],
            "saldo": reporte["saldo_final"],
        },
    ]
    return filas_a_csv(_CSV_COLUMNAS, filas)


@router.get("/{cuenta_id}", response_model=None)
def obtener_libro_mayor(
    cuenta_id: int,
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    formato: Literal["json", "csv"] = Query(default="json"),
    db: Session = Depends(get_db),
) -> LibroMayorResponse | Response:
    cuenta = crud.cuenta.get(db, cuenta_id)
    if cuenta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_desde no puede ser posterior a fecha_hasta",
        )
    reporte = crud.libro_mayor.get_libro_mayor(
        db, cuenta=cuenta, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )
    if formato == "csv":
        return csv_response(
            _a_csv(reporte), nombre_archivo=f"libro_mayor_{cuenta.codigo}.csv"
        )
    return LibroMayorResponse.model_validate(reporte)
