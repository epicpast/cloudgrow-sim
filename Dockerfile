# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src/ ./src/
COPY README.md ./

# Install the project
RUN uv sync --frozen --no-dev


FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Copy source for any runtime needs
COPY --from=builder /app/src ./src

# Default command (can be overridden)
ENTRYPOINT ["python", "-m", "cloudgrow_sim"]
CMD ["--help"]
