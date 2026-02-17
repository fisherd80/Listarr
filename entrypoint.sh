#!/bin/bash
set -e

# Listarr Docker Entrypoint
# Fixes bind mount permissions and drops from root to non-root user

if [ "$(id -u)" = "0" ]; then
    # Running as root - fix permissions for bind-mounted instance directory
    echo "[INFO] Fixing permissions for /app/instance..."
    chown -R listarr:listarr /app/instance

    # Run setup as listarr user (generates keys and database if needed)
    echo "[INFO] Running setup..."
    gosu listarr python setup.py

    # Drop privileges and exec the main command
    echo "[INFO] Starting application as user listarr (UID 1000)..."
    exec gosu listarr "$@"
else
    # Already running as non-root (e.g., Kubernetes securityContext, rootless Docker)
    echo "[INFO] Running as UID $(id -u)"
    python setup.py
    exec "$@"
fi
