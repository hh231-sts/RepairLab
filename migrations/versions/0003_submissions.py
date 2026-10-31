"""Idempotent submissions and atomic experiment launch state."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    # 0001 imports the current metadata on fresh installations; older DBs need columns.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "submission_key" not in {c["name"] for c in inspector.get_columns("runs")}:
        op.add_column("runs", sa.Column("submission_key", sa.String(100), nullable=True))
        op.create_index("run_submission_key", "runs", ["submission_key"], unique=True)
    if "launched" not in {c["name"] for c in inspector.get_columns("experiments")}:
        op.add_column(
            "experiments", sa.Column("launched", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade():
    op.drop_column("runs", "submission_key")
    op.drop_column("experiments", "launched")
