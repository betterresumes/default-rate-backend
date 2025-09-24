# Production Dockerfile for Railway
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
  gcc \
  curl \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean

# Copy requirements first for better Docker layer caching
COPY requirements.prod.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.prod.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x deployment/scripts/start-railway.sh deployment/scripts/start-worker.sh

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Railway sets PORT env var)
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Production command
CMD ["./deployment/scripts/start-railway.sh"]
