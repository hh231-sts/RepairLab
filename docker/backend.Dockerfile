FROM python:3.12.13-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.11.17 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY backend ./backend
RUN uv sync --frozen --no-dev
COPY alembic.ini ./
COPY migrations ./migrations
COPY fixtures ./fixtures
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "repairlab.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
