from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.cuenta import NaturalezaCuenta


class BalanceComprobacionFila(BaseModel):
    cuenta_id: int
    codigo: str
    nombre: str
    naturaleza: NaturalezaCuenta
    saldo_inicial: Decimal
    debito: Decimal
    credito: Decimal
    saldo_final: Decimal


class BalanceComprobacionResponse(BaseModel):
    fecha_desde: date | None
    fecha_hasta: date | None
    cuentas: list[BalanceComprobacionFila]
    total_debitos: Decimal
    total_creditos: Decimal
    balanceado: bool
