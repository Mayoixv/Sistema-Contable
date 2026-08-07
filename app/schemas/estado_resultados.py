from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class EstadoResultadosFila(BaseModel):
    cuenta_id: int
    codigo: str
    nombre: str
    monto: Decimal


class EstadoResultadosResponse(BaseModel):
    fecha_desde: date | None
    fecha_hasta: date | None
    ingresos: list[EstadoResultadosFila]
    costos: list[EstadoResultadosFila]
    gastos: list[EstadoResultadosFila]
    total_ingresos: Decimal
    total_costos: Decimal
    total_gastos: Decimal
    utilidad_bruta: Decimal
    utilidad_neta: Decimal
