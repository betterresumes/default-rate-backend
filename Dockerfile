# Railway Production Dockerfile
# Optimized for Railway deployment with Neon PostgreSQL

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables for Railway
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Install system dependencies required for PostgreSQL and ML packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.prod.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.prod.txt

# Copy the application code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Switch to non-root user
USER appuser

# Expose the port that Railway will use
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Command to run the application
CMD ["./start.sh"]
