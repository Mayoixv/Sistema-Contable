from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db
from app.schemas.estado_resultados import EstadoResultadosResponse
from app.utils.csv_export import csv_response, filas_a_csv

router = APIRouter(prefix="/estado-resultados", tags=["Estado de resultados"])

_CSV_COLUMNAS = ["seccion", "codigo", "nombre", "monto"]


def _a_csv(reporte: dict) -> str:
    filas: list[dict] = []
    for seccion, clave in (("ingreso", "ingresos"), ("costo", "costos"), ("gasto", "gastos")):
        for fila in reporte[clave]:
            filas.append({"seccion": seccion, **fila})
    for etiqueta, clave in (
        ("TOTAL INGRESOS", "total_ingresos"),
        ("TOTAL COSTOS", "total_costos"),
        ("UTILIDAD BRUTA", "utilidad_bruta"),
        ("TOTAL GASTOS", "total_gastos"),
        ("UTILIDAD NETA", "utilidad_neta"),
    ):
        filas.append({"seccion": "", "codigo": "", "nombre": etiqueta, "monto": reporte[clave]})
    return filas_a_csv(_CSV_COLUMNAS, filas)


@router.get("/", response_model=None)
def obtener_estado_resultados(
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    formato: Literal["json", "csv"] = Query(default="json"),
    db: Session = Depends(get_db),
) -> EstadoResultadosResponse | Response:
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_desde no puede ser posterior a fecha_hasta",
        )
    reporte = crud.estado_resultados.get_estado_resultados(
        db, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )
    if formato == "csv":
        return csv_response(_a_csv(reporte), nombre_archivo="estado_resultados.csv")
    return EstadoResultadosResponse.model_validate(reporte)
