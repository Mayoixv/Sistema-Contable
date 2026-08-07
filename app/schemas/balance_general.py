from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class BalanceGeneralFila(BaseModel):
    cuenta_id: int
    codigo: str
    nombre: str
    saldo: Decimal


class BalanceGeneralResponse(BaseModel):
    fecha_corte: date | None
    activos: list[BalanceGeneralFila]
    pasivos: list[BalanceGeneralFila]
    patrimonio: list[BalanceGeneralFila]
    resultado_acumulado: Decimal
    total_activo: Decimal
    total_pasivo: Decimal
    total_patrimonio: Decimal
    total_pasivo_mas_patrimonio: Decimal
    balanceado: bool
