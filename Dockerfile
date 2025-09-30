FROM python:3.11-slim as base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN python -m pip install --upgrade pip --retries 5 --timeout 30

COPY requirements.prod.txt .

RUN pip install --no-cache-dir \
    --retries 5 \
    --timeout 300 \
    -r requirements.prod.txt

COPY . .

RUN chmod +x start.sh deployment/scripts/start-worker.sh

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE $PORT

HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["./start.sh"]
