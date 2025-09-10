FROM python:3.11-slim

# Environment settings
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libfreetype6-dev libjpeg-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Create virtual environment and install Python dependencies
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY requirements.txt .
RUN uv pip install -r requirements.txt

# Copy application source and pre-cached embedding models
COPY src/ ./src
COPY models/ /root/.cache/chroma/

# Generate data only if database doesn't exist
RUN test -f ./src/business.sqlite || python -m src.data_generation

# Create reports directory
RUN mkdir -p /app/reports

# Add non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "src.business_agents"]
