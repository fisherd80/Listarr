# ===========================
# Listarr Dockerfile
# ===========================
# Multi-stage build for optimized production image

# ===========================
# Stage 1: Build Stage
# ===========================
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir --user -r requirements.txt

# ===========================
# Stage 2: Production Stage
# ===========================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=listarr \
    PORT=5000

# Install su-exec for privilege dropping in entrypoint (no Go dependency)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev curl && \
    curl -fsSL https://raw.githubusercontent.com/ncopa/su-exec/v0.2/su-exec.c -o /tmp/su-exec.c && \
    gcc -Wall -o /usr/local/bin/su-exec /tmp/su-exec.c && \
    rm -f /tmp/su-exec.c && \
    apt-get purge -y --auto-remove gcc libc6-dev curl && \
    rm -rf /var/lib/apt/lists/* && \
    su-exec nobody true

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

# Copy entrypoint script (must be executable, owned by root)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Add local Python packages to PATH
ENV PATH=/home/listarr/.local/bin:$PATH

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; r=requests.get('http://localhost:5000/health', timeout=5); r.raise_for_status()" || exit 1

# Default non-root user (docker-compose overrides to root for bind-mount permission fixing)
USER listarr

# Entrypoint handles permissions and privilege drop
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn_config.py", "listarr:create_app()"]
