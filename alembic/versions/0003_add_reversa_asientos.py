"""add reversa_de_id to asientos (reversión de asientos)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("asientos", sa.Column("reversa_de_id", sa.Integer(), nullable=True))
    op.create_index("ix_asientos_reversa_de_id", "asientos", ["reversa_de_id"])
    op.create_foreign_key(
        "fk_asientos_reversa_de_id_asientos",
        "asientos",
        "asientos",
        ["reversa_de_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_asientos_reversa_de_id_asientos", "asientos", type_="foreignkey")
    op.drop_index("ix_asientos_reversa_de_id", table_name="asientos")
    op.drop_column("asientos", "reversa_de_id")
