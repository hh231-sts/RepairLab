"""Initial durable ledger, project-scoped FTS and vector store."""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = "postgresql" if bind.dialect.name == "postgresql" else "sqlite"
    sql = (Path(__file__).resolve().parents[1] / "sql" / (dialect + ".sql")).read_text("utf-8")
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute(
            "CREATE TABLE document_vectors (document_id varchar(64) PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE, embedding vector(384) NOT NULL, source varchar(80) NOT NULL)"
        )
        op.execute(
            "CREATE INDEX document_vector_hnsw ON document_vectors USING hnsw (embedding vector_cosine_ops)"
        )
        op.execute("CREATE INDEX document_fts ON documents USING gin (to_tsvector('simple',content))")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TABLE document_vectors")
    for name in [
        "receipts",
        "verifications",
        "model_calls",
        "events",
        "artifacts",
        "agents",
        "runs",
        "issues",
        "memories",
        "documents",
        "projects",
        "skills",
        "experiments",
    ]:
        op.execute("DROP TABLE IF EXISTS " + name)
