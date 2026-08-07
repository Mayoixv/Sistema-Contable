"""create cuentas table (plan de cuentas jerárquico)

Revision ID: 0001
Revises:
Create Date: 2026-08-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cuentas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "activo",
                "pasivo",
                "patrimonio",
                "ingreso",
                "gasto",
                "costo",
                name="tipo_cuenta",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column(
            "naturaleza",
            sa.Enum(
                "deudora",
                "acreedora",
                name="naturaleza_cuenta",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("nivel", sa.Integer(), nullable=False),
        sa.Column("padre_id", sa.Integer(), nullable=True),
        sa.Column("acepta_movimiento", sa.Boolean(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["padre_id"], ["cuentas.id"], name="fk_cuentas_padre_id_cuentas", ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("codigo", name="uq_cuentas_codigo"),
        sa.CheckConstraint("nivel >= 1", name="ck_cuentas_nivel_positivo"),
    )
    op.create_index("ix_cuentas_codigo", "cuentas", ["codigo"])
    op.create_index("ix_cuentas_padre_id", "cuentas", ["padre_id"])


def downgrade() -> None:
    op.drop_index("ix_cuentas_padre_id", table_name="cuentas")
    op.drop_index("ix_cuentas_codigo", table_name="cuentas")
    op.drop_table("cuentas")
