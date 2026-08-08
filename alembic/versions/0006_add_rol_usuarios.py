"""add rol to usuarios (roles y permisos)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # OJO con las mayúsculas: SQLAlchemy guarda el NOMBRE del miembro del
    # enum ('CONTADOR'), no su valor ('contador'), igual que las columnas
    # cuentas.tipo/naturaleza que ya existen. Escribir el valor en minúscula
    # inserta datos que el ORM después no puede leer ("'admin' is not among
    # the defined enum values").
    op.add_column(
        "usuarios",
        sa.Column(
            "rol",
            sa.String(length=20),
            nullable=False,
            server_default="CONTADOR",
        ),
    )
    # Los usuarios que ya existían son los operadores iniciales del sistema:
    # si quedaran como contador, nadie podría dar de alta a nadie más y el
    # sistema quedaría sin administración.
    op.execute("UPDATE usuarios SET rol = 'ADMIN'")


def downgrade() -> None:
    op.drop_column("usuarios", "rol")
