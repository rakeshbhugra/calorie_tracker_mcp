FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY uv.lock* .
COPY README.md .
COPY src/ src/
COPY main.py .

# Install dependencies (creates venv and installs)
RUN uv sync --no-dev

# Expose port
EXPOSE 8000

# Run the server
CMD ["uv", "run", "python", "-m", "calorie_tracker.server"]
