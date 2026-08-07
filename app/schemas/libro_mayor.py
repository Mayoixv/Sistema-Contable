from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.cuenta import NaturalezaCuenta


class LibroMayorLinea(BaseModel):
    asiento_id: int
    asiento_numero: int
    fecha: date
    descripcion: str | None
    debito: Decimal
    credito: Decimal
    saldo: Decimal


class LibroMayorResponse(BaseModel):
    cuenta_id: int
    codigo: str
    nombre: str
    naturaleza: NaturalezaCuenta
    fecha_desde: date | None
    fecha_hasta: date | None
    saldo_inicial: Decimal
    movimientos: list[LibroMayorLinea]
    total_debitos: Decimal
    total_creditos: Decimal
    saldo_final: Decimal
