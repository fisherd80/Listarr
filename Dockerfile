# ===========================
# Listarr Dockerfile
# ===========================
# Multi-stage build for optimized production image

# ===========================
# Stage 1: Build Stage
# ===========================
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ===========================
# Stage 2: Production Stage
# ===========================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=listarr \
    PORT=5000

# Create non-root user for security
RUN useradd -m -u 1000 listarr && \
    mkdir -p /app /app/instance && \
    chown -R listarr:listarr /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/listarr/.local

# Copy application code
COPY --chown=listarr:listarr . .

# Switch to non-root user
USER listarr

# Add local Python packages to PATH
ENV PATH=/home/listarr/.local/bin:$PATH

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/', timeout=5)" || exit 1

# Run setup on first start (if key doesn't exist), then start application
CMD python setup.py && \
    gunicorn --bind 0.0.0.0:5000 \
             --workers 2 \
             --threads 4 \
             --timeout 120 \
             --access-logfile - \
             --error-logfile - \
             'listarr:create_app()'
