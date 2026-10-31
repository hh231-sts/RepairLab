"""OCI image IDs include a sha256: prefix."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column("verifications", "environment_hash", type_=sa.String(100))


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column("verifications", "environment_hash", type_=sa.String(64))
