# ===========================
# Listarr Dockerfile
# ===========================
# Multi-stage build for optimized production image

# ===========================
# Stage 1: Build Stage
# ===========================
FROM python:3-alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apk upgrade --no-cache && \
    apk add --no-cache gcc musl-dev

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir --user -r requirements.txt

# ===========================
# Stage 2: Production Stage
# ===========================
FROM python:3-alpine

# Version injected at build time for tag releases (e.g. --build-arg APP_VERSION=2.1.0)
ARG APP_VERSION=dev

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=listarr \
    PORT=5000

ENV APP_VERSION=${APP_VERSION}

# Upgrade base packages, compile su-exec, then remove build deps
RUN apk upgrade --no-cache && \
    apk add --no-cache gcc musl-dev curl && \
    curl -fsSL https://raw.githubusercontent.com/ncopa/su-exec/v0.2/su-exec.c -o /tmp/su-exec.c && \
    gcc -Wall -o /usr/local/bin/su-exec /tmp/su-exec.c && \
    rm -f /tmp/su-exec.c && \
    apk del gcc musl-dev curl && \
    su-exec nobody true

# Upgrade pip in the runtime stage (builder upgrade doesn't carry over)
RUN pip install --no-cache-dir --upgrade pip

# Create non-root user for security (Alpine uses adduser, not useradd)
RUN adduser -D -u 1000 listarr && \
    mkdir -p /app /app/instance && \
    chown -R listarr:listarr /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/listarr/.local

# Copy application code
COPY --chown=listarr:listarr . .

# Copy entrypoint script (must be executable, owned by root)
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Add local Python packages to PATH
ENV PATH=/home/listarr/.local/bin:$PATH

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=5)" || exit 1

# Note: no USER directive here - entrypoint starts as root to fix bind-mount permissions,
# then drops to listarr via su-exec. Setting USER listarr here breaks Unraid deployments.

# Entrypoint handles permissions and privilege drop
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--config", "config/gunicorn_config.py", "listarr:create_app()"]
