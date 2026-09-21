# FastAPI backend. Python 3.13 with uv, dependencies from the lockfile, no dev tools.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/jev.db

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app

RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/meta', timeout=2)"]

CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
