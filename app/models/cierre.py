from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Cierre(Base):
    """Cierre de ejercicio: salda las cuentas nominales contra patrimonio.

    Guarda el asiento generado (no lo recalcula) para que quede auditable
    exactamente qué se cerró, cuándo y por cuánto.
    """

    __tablename__ = "cierres"
    __table_args__ = (UniqueConstraint("fecha_cierre", name="uq_cierres_fecha"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha_cierre: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # RESTRICT: borrar el asiento de cierre dejaría el registro sin respaldo
    # y las cuentas nominales des-saldadas sin que nadie se entere.
    asiento_id: Mapped[int] = mapped_column(
        ForeignKey("asientos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cuenta_resultado_id: Mapped[int] = mapped_column(
        ForeignKey("cuentas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    utilidad_neta: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    asiento: Mapped["Asiento"] = relationship("Asiento")
    cuenta_resultado: Mapped["Cuenta"] = relationship("Cuenta")
    usuario: Mapped["Usuario | None"] = relationship("Usuario")

    def __repr__(self) -> str:
        return f"<Cierre {self.fecha_cierre} utilidad={self.utilidad_neta}>"
