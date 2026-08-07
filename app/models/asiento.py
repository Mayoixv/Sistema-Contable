from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Asiento(Base):
    """Encabezado de un asiento contable (unidad de partida doble)."""

    __tablename__ = "asientos"
    __table_args__ = (UniqueConstraint("numero", name="uq_asientos_numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Un asiento no se corrige in-place: se "reversa" generando un nuevo
    # asiento con los montos invertidos. reversa_de_id apunta al asiento
    # original cuando este ES una reversión; reversiones es la lista (en la
    # práctica, a lo sumo un elemento) de asientos que reversan a este.
    reversa_de_id: Mapped[int | None] = mapped_column(
        ForeignKey("asientos.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Las líneas pertenecen por completo al asiento: se crean, leen y borran
    # junto con él (no existe edición de una línea suelta).
    movimientos: Mapped[list["MovimientoContable"]] = relationship(
        "MovimientoContable",
        back_populates="asiento",
        cascade="all, delete-orphan",
        order_by="MovimientoContable.id",
    )
    reversa_de: Mapped["Asiento | None"] = relationship(
        "Asiento", remote_side=[id], back_populates="reversiones"
    )
    reversiones: Mapped[list["Asiento"]] = relationship("Asiento", back_populates="reversa_de")

    @property
    def reversado_por_id(self) -> int | None:
        return self.reversiones[0].id if self.reversiones else None

    def __repr__(self) -> str:
        return f"<Asiento #{self.numero} {self.fecha}>"


class MovimientoContable(Base):
    """Línea de un asiento: movimiento de débito o de crédito sobre una cuenta."""

    __tablename__ = "movimientos_contables"
    __table_args__ = (
        CheckConstraint(
            "debito >= 0 AND credito >= 0", name="ck_movimientos_montos_no_negativos"
        ),
        CheckConstraint(
            "NOT (debito > 0 AND credito > 0)", name="ck_movimientos_no_debito_y_credito"
        ),
        CheckConstraint("debito > 0 OR credito > 0", name="ck_movimientos_monto_requerido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asiento_id: Mapped[int] = mapped_column(
        ForeignKey("asientos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cuenta_id: Mapped[int] = mapped_column(
        ForeignKey("cuentas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    debito: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    credito: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)

    asiento: Mapped["Asiento"] = relationship("Asiento", back_populates="movimientos")
    cuenta: Mapped["Cuenta"] = relationship("Cuenta", back_populates="movimientos")

    def __repr__(self) -> str:
        return (
            f"<MovimientoContable asiento={self.asiento_id} cuenta={self.cuenta_id} "
            f"D={self.debito} C={self.credito}>"
        )
