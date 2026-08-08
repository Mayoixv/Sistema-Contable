from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.movimiento import MovimientoCreate, MovimientoRead


class AsientoCreate(BaseModel):
    fecha: date
    descripcion: str = Field(..., min_length=1)
    movimientos: list[MovimientoCreate] = Field(..., min_length=2)

    @model_validator(mode="after")
    def _partida_doble_balanceada(self) -> "AsientoCreate":
        total_debito = sum((m.debito for m in self.movimientos), Decimal("0"))
        total_credito = sum((m.credito for m in self.movimientos), Decimal("0"))
        if total_debito != total_credito:
            raise ValueError(
                "El asiento no está balanceado: "
                f"débitos={total_debito} != créditos={total_credito}"
            )
        return self


class AsientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: int
    fecha: date
    descripcion: str
    created_at: datetime
    reversa_de_id: int | None
    reversado_por_id: int | None
    usuario_id: int | None
    usuario_email: str | None
    movimientos: list[MovimientoRead]


class AsientoListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AsientoRead]
