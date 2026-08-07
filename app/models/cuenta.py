import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class TipoCuenta(str, enum.Enum):
    ACTIVO = "activo"
    PASIVO = "pasivo"
    PATRIMONIO = "patrimonio"
    INGRESO = "ingreso"
    GASTO = "gasto"
    COSTO = "costo"


class NaturalezaCuenta(str, enum.Enum):
    DEUDORA = "deudora"
    ACREEDORA = "acreedora"


# Naturaleza contable por defecto según el tipo de cuenta. Se usa como valor
# sugerido al crear una cuenta; se permite sobrescribirla explícitamente para
# soportar cuentas de naturaleza contraria (ej. depreciación acumulada, un
# Activo de naturaleza acreedora).
NATURALEZA_POR_TIPO: dict[TipoCuenta, NaturalezaCuenta] = {
    TipoCuenta.ACTIVO: NaturalezaCuenta.DEUDORA,
    TipoCuenta.GASTO: NaturalezaCuenta.DEUDORA,
    TipoCuenta.COSTO: NaturalezaCuenta.DEUDORA,
    TipoCuenta.PASIVO: NaturalezaCuenta.ACREEDORA,
    TipoCuenta.PATRIMONIO: NaturalezaCuenta.ACREEDORA,
    TipoCuenta.INGRESO: NaturalezaCuenta.ACREEDORA,
}


class Cuenta(Base):
    """Nodo del plan de cuentas jerárquico (árbol de cuentas contables)."""

    __tablename__ = "cuentas"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_cuentas_codigo"),
        CheckConstraint("nivel >= 1", name="ck_cuentas_nivel_positivo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo: Mapped[TipoCuenta] = mapped_column(
        SAEnum(TipoCuenta, name="tipo_cuenta", native_enum=False, length=20),
        nullable=False,
    )
    naturaleza: Mapped[NaturalezaCuenta] = mapped_column(
        SAEnum(NaturalezaCuenta, name="naturaleza_cuenta", native_enum=False, length=20),
        nullable=False,
    )
    nivel: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    padre_id: Mapped[int | None] = mapped_column(
        ForeignKey("cuentas.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    # Solo las cuentas "de detalle" (hojas) pueden recibir movimientos de
    # asientos contables; las cuentas "sumaria" (con hijas) agrupan saldos.
    acepta_movimiento: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    padre: Mapped["Cuenta | None"] = relationship(
        "Cuenta", remote_side=[id], back_populates="hijas"
    )
    hijas: Mapped[list["Cuenta"]] = relationship(
        "Cuenta", back_populates="padre", order_by="Cuenta.codigo"
    )
    movimientos: Mapped[list["MovimientoContable"]] = relationship(
        "MovimientoContable", back_populates="cuenta"
    )

    def __repr__(self) -> str:
        return f"<Cuenta {self.codigo} - {self.nombre}>"
