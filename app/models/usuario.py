from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (UniqueConstraint("email", name="uq_usuarios_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # passive_deletes="all": sin esto, al borrar un usuario SQLAlchemy pone
    # usuario_id=NULL en sus asientos y el borrado "funciona", dejándolos sin
    # autor. Con esto no toca las hijas y deja actuar al ON DELETE RESTRICT
    # de la base, que es lo que preserva la trazabilidad.
    asientos: Mapped[list["Asiento"]] = relationship(
        "Asiento", back_populates="usuario", passive_deletes="all"
    )

    def __repr__(self) -> str:
        return f"<Usuario {self.email}>"
