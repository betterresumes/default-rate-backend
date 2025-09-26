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

# Install system dependencies required for PostgreSQL and ML packages (including LightGBM)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    gcc \
    g++ \
    cmake \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.prod.txt .

# Install Python dependencies with explicit LightGBM installation
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir lightgbm==4.6.0 --verbose && \
    pip install --no-cache-dir -r requirements.prod.txt

# Copy the application code
COPY . .

# Verify that quarterly ML models can be loaded (this will catch LightGBM issues early)
RUN python -c "import sys; sys.path.insert(0, '/app'); from app.services.quarterly_ml_service import QuarterlyMLModelService; service = QuarterlyMLModelService(); print('✅ Quarterly ML models loaded successfully in Docker build')"

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
