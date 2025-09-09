FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libfreetype6-dev libjpeg-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Create virtual environment
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY requirements.txt .
RUN uv pip install -r requirements.txt

COPY src/ ./src

# Copy pre-cached embedding model
COPY models/ /root/.cache/chroma/

# Generate data only if database doesn't exist  
RUN test -f ./src/business.sqlite || python -m src.data_generation

# Create reports directory
RUN mkdir -p /app/reports

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "src.business_agents"]
