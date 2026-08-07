from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MovimientoCreate(BaseModel):
    cuenta_id: int
    debito: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    credito: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    descripcion: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _un_solo_lado(self) -> "MovimientoCreate":
        if self.debito > 0 and self.credito > 0:
            raise ValueError("Un movimiento no puede tener débito y crédito a la vez")
        if self.debito == 0 and self.credito == 0:
            raise ValueError("Un movimiento debe tener débito o crédito mayor a cero")
        return self


class MovimientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cuenta_id: int
    debito: Decimal
    credito: Decimal
    descripcion: str | None
