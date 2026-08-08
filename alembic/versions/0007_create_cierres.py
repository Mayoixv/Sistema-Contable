"""create cierres y flag es_cierre en asientos (cierre de ejercicio)

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "asientos",
        sa.Column(
            "es_cierre", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )

    op.create_table(
        "cierres",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fecha_cierre", sa.Date(), nullable=False),
        sa.Column("asiento_id", sa.Integer(), nullable=False),
        sa.Column("cuenta_resultado_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("utilidad_neta", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["asiento_id"], ["asientos.id"], name="fk_cierres_asiento_id", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["cuenta_resultado_id"],
            ["cuentas.id"],
            name="fk_cierres_cuenta_resultado_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuarios.id"], name="fk_cierres_usuario_id", ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("fecha_cierre", name="uq_cierres_fecha"),
    )
    op.create_index("ix_cierres_fecha_cierre", "cierres", ["fecha_cierre"])
    op.create_index("ix_cierres_asiento_id", "cierres", ["asiento_id"])
    op.create_index("ix_cierres_cuenta_resultado_id", "cierres", ["cuenta_resultado_id"])
    op.create_index("ix_cierres_usuario_id", "cierres", ["usuario_id"])


def downgrade() -> None:
    op.drop_table("cierres")
    op.drop_column("asientos", "es_cierre")
