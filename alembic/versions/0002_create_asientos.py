"""create asientos and movimientos_contables tables (partida doble)

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "asientos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("numero", name="uq_asientos_numero"),
    )
    op.create_index("ix_asientos_numero", "asientos", ["numero"])
    op.create_index("ix_asientos_fecha", "asientos", ["fecha"])

    op.create_table(
        "movimientos_contables",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asiento_id", sa.Integer(), nullable=False),
        sa.Column("cuenta_id", sa.Integer(), nullable=False),
        sa.Column("debito", sa.Numeric(14, 2), nullable=False),
        sa.Column("credito", sa.Numeric(14, 2), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["asiento_id"],
            ["asientos.id"],
            name="fk_movimientos_asiento_id_asientos",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cuenta_id"],
            ["cuentas.id"],
            name="fk_movimientos_cuenta_id_cuentas",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "debito >= 0 AND credito >= 0", name="ck_movimientos_montos_no_negativos"
        ),
        sa.CheckConstraint(
            "NOT (debito > 0 AND credito > 0)", name="ck_movimientos_no_debito_y_credito"
        ),
        sa.CheckConstraint("debito > 0 OR credito > 0", name="ck_movimientos_monto_requerido"),
    )
    op.create_index("ix_movimientos_asiento_id", "movimientos_contables", ["asiento_id"])
    op.create_index("ix_movimientos_cuenta_id", "movimientos_contables", ["cuenta_id"])


def downgrade() -> None:
    op.drop_index("ix_movimientos_cuenta_id", table_name="movimientos_contables")
    op.drop_index("ix_movimientos_asiento_id", table_name="movimientos_contables")
    op.drop_table("movimientos_contables")
    op.drop_index("ix_asientos_fecha", table_name="asientos")
    op.drop_index("ix_asientos_numero", table_name="asientos")
    op.drop_table("asientos")
