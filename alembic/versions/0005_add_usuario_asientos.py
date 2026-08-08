"""add usuario_id to asientos (auditoría: quién cargó el asiento)

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: los asientos cargados antes de que existiera la
    # autenticación no tienen autor conocido y no se puede inventar uno.
    op.add_column("asientos", sa.Column("usuario_id", sa.Integer(), nullable=True))
    op.create_index("ix_asientos_usuario_id", "asientos", ["usuario_id"])
    op.create_foreign_key(
        "fk_asientos_usuario_id_usuarios",
        "asientos",
        "usuarios",
        ["usuario_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_asientos_usuario_id_usuarios", "asientos", type_="foreignkey")
    op.drop_index("ix_asientos_usuario_id", table_name="asientos")
    op.drop_column("asientos", "usuario_id")
