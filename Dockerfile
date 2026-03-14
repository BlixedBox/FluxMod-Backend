FROM python:3.12.10-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 UV_PYTHON_DOWNLOADS=0


WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

FROM python:3.12.10-slim AS runtime

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app /app

EXPOSE 8000

CMD ["python", "-m", "gunicorn", "api2:create_app()", "--bind", "0.0.0.0:8000", "--workers", "1"]