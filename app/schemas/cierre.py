from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CierreCreate(BaseModel):
    fecha_cierre: date
    cuenta_resultado_id: int = Field(
        ...,
        description=(
            "Cuenta de patrimonio que recibe el resultado del ejercicio "
            "(ej. 'Resultados acumulados')"
        ),
    )


class CierreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_cierre: date
    asiento_id: int
    cuenta_resultado_id: int
    usuario_id: int | None
    utilidad_neta: Decimal
    created_at: datetime
