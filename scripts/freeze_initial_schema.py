"""Maintainer helper: generate the immutable initial schema migration SQL (review before committing)."""

from pathlib import Path

from repairlab.db import Base
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

folder = Path(__file__).resolve().parents[1] / "migrations" / "sql"
folder.mkdir(exist_ok=True)
for name, dialect in [("postgresql", postgresql.dialect()), ("sqlite", sqlite.dialect())]:
    statements = []
    for table in Base.metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        statements.extend(
            str(CreateIndex(index).compile(dialect=dialect)).strip() + ";"
            for index in sorted(table.indexes, key=lambda i: i.name)
        )
    (folder / (name + ".sql")).write_text("\n\n".join(statements) + "\n", "utf-8")
