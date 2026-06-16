FROM python:3.11-bookworm

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install system dependencies for Playwright
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libgtk-3-0 \
        libgbm1 \
        libasound2 \
        curl \
        libdbus-glib-1-2 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install --upgrade pip && pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock /app/

# Install Python dependencies using uv
RUN uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY . /app/

# Set the entrypoint to use uvicorn from the venv
ENTRYPOINT ["/app/.venv/bin/uvicorn"]

CMD ["main:app", "--host", "0.0.0.0", "--port", "8023"]
