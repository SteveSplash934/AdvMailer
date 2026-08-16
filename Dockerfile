FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Enable bytecode compilation for performance
ENV UV_COMPILE_BYTECODE=1

# Copy manifest files first for Docker layer caching
COPY pyproject.toml uv.lock .python-version ./

# Install dependencies using frozen lockfile
RUN uv sync --frozen --no-dev

# Copy application source code
COPY . .

# Expose production port
EXPOSE 5000

ENV HOST=0.0.0.0
ENV PORT=5000

# Launch application via Gunicorn WSGI
CMD ["uv", "run", "gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120"]