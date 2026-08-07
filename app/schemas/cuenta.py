from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.cuenta import NATURALEZA_POR_TIPO, NaturalezaCuenta, TipoCuenta


class CuentaBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20, examples=["1.1.01"])
    nombre: str = Field(..., min_length=1, max_length=150)
    tipo: TipoCuenta
    naturaleza: NaturalezaCuenta | None = None
    acepta_movimiento: bool = True
    activa: bool = True
    descripcion: str | None = None
    padre_id: int | None = None

    @model_validator(mode="after")
    def _completar_naturaleza(self) -> "CuentaBase":
        if self.naturaleza is None:
            self.naturaleza = NATURALEZA_POR_TIPO[self.tipo]
        return self


class CuentaCreate(CuentaBase):
    pass


class CuentaUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    tipo: TipoCuenta | None = None
    naturaleza: NaturalezaCuenta | None = None
    acepta_movimiento: bool | None = None
    activa: bool | None = None
    descripcion: str | None = None
    padre_id: int | None = None


class CuentaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    tipo: TipoCuenta
    naturaleza: NaturalezaCuenta
    nivel: int
    padre_id: int | None
    acepta_movimiento: bool
    activa: bool
    descripcion: str | None
    created_at: datetime
    updated_at: datetime


class CuentaTree(CuentaRead):
    hijas: list["CuentaTree"] = []


CuentaTree.model_rebuild()
