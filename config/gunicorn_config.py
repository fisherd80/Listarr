"""Gunicorn configuration file for Listarr.

Worker scheduler pattern:
- The first worker (age == 1) is designated as the scheduler worker
- Only this worker will run the scheduler to prevent duplicate job execution
- SCHEDULER_WORKER environment variable is set to 'true' or 'false' accordingly
"""

import os

# Server socket
bind = "0.0.0.0:5000"

# Worker processes
worker_class = "gthread"
workers = 2
threads = 4
timeout = 120

# Disable control socket — not needed in containerized deployment
control_socket_disable = True

# Logging - only log errors (4xx/5xx), not successful requests
errorlog = "-"  # stderr


class ErrorOnlyFilter:
    """Filter that only allows error status codes (4xx and 5xx)."""

    def filter(self, record):
        # Access log records have the status code in the message
        # Format: '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
        # where %(s)s is the status code
        if hasattr(record, "args") and isinstance(record.args, dict):
            status = record.args.get("s", "200")
            try:
                status_code = int(status)
                return status_code >= 400
            except (ValueError, TypeError):
                return True
        return True


# Custom access log class that filters out successful requests
accesslog = "-" if os.environ.get("LOG_ACCESS_REQUESTS", "").lower() == "true" else None


def post_request(worker, req, environ, resp):
    """Log only error responses (4xx and 5xx)."""
    status_code = int(resp.status.split()[0])
    if status_code >= 400:
        worker.log.info(
            '%s %s "%s %s" %s %s',
            environ.get("REMOTE_ADDR", "-"),
            environ.get("HTTP_HOST", "-"),
            req.method,
            req.path,
            resp.status,
            resp.sent or "-",
        )


def post_fork(server, worker):
    """Identify first worker for scheduler initialization.

    Only the first worker (age == 1) runs the scheduler to prevent
    duplicate job execution across multiple workers.
    """
    import os

    if worker.age == 1:
        os.environ["SCHEDULER_WORKER"] = "true"
        worker.log.info("This worker will run the scheduler")
    else:
        os.environ["SCHEDULER_WORKER"] = "false"
