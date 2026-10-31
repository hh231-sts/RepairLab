"""Serialize reservations against the total project cost ceiling."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("budget_pool"):
        op.create_table(
            "budget_pool",
            sa.Column("id", sa.String(24), primary_key=True),
            sa.Column("limit_cny", sa.Float(), nullable=False),
            sa.Column("spent", sa.Float(), nullable=False),
            sa.Column("reserved", sa.Float(), nullable=False),
        )


def downgrade():
    op.drop_table("budget_pool")
