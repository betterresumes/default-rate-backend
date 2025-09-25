# Production Dockerfile for Railway
# Use existing local Python image to avoid Docker Hub authentication issues
# syntax=docker/dockerfile:1
FROM backend-fastapi-app:latest

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Update existing packages and install additional dependencies if needed
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.prod.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.prod.txt

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
