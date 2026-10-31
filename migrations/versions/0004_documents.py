"""Track independent document provenance/version alongside repository commit."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("documents")}
    if "source_version" not in columns:
        op.add_column(
            "documents", sa.Column("source_version", sa.String(100), server_default="", nullable=False)
        )
    if "origin" not in columns:
        op.add_column(
            "documents", sa.Column("origin", sa.String(24), server_default="repository", nullable=False)
        )


def downgrade():
    op.drop_column("documents", "origin")
    op.drop_column("documents", "source_version")
