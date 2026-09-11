#!/bin/sh
# Credential-free smoke test for the Listarr Docker image (D-07).
#
# Proves, against a freshly built image, that:
#   1. gunicorn boots and /health returns 200
#   2. the entrypoint's root -> listarr privilege drop actually happens
#   3. the scheduler worker initializes (post_fork / SCHEDULER_WORKER path)
#   4. ZoneInfo resolves via the `tzdata` pip wheel alone, not the Alpine
#      apk package (purged first, so this cannot false-green)
#   5. a Fernet encrypt/decrypt round-trip succeeds
#
# The destructive ZoneInfo purge (step 4) intentionally runs after the
# non-destructive checks (1-3) so a reordering bug cannot make an unrelated
# check fail because timezone data was already deleted. Step 5 does not
# touch tzdata, so it is order-agnostic relative to step 4.
#
# Usage: ./scripts/docker-smoke.sh [image[:tag]]
#
# Windows note: this is a POSIX sh script — run it via Git Bash, e.g.
#   bash ./scripts/docker-smoke.sh listarr:ci
# Native PowerShell can't exec it directly and doesn't chain `&&` the same
# way as sh/bash; run the build and this script as two separate commands.
set -eu

IMAGE="${1:-listarr:ci}"
NAME="listarr-smoke-$$"

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Boot detached (entrypoint starts as root, su-exec drops to listarr).
docker run -d --name "$NAME" -p 5000:5000 "$IMAGE" >/dev/null

# 1. Wait for gunicorn + /health 200 (<=30s).
health_ok=0
i=1
while [ "$i" -le 30 ]; do
  if docker exec "$NAME" python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:5000/health',timeout=2).status==200 else 1)" >/dev/null 2>&1; then
    health_ok=1
    break
  fi
  i=$((i + 1))
  sleep 1
done
if [ "$health_ok" -ne 1 ]; then
  echo "health: FAIL"
  docker logs "$NAME" || true
  exit 1
fi
echo "health: OK"

# 2. Privilege drop: main gunicorn process runs as listarr (uid 1000), not root.
#    `docker exec` without --user always attaches as root (the image has no
#    USER directive by design — see Dockerfile comment), so `docker exec ...
#    id` only reports the exec session's default user, never the actual
#    running process owner. Use `docker top`, which reads the host-visible
#    process table and reflects the real post-su-exec UID.
if ! docker top "$NAME" | awk 'NR>1 {print $1}' | grep -qx 1000; then
  echo "user: FAIL"
  docker top "$NAME" || true
  docker logs "$NAME" || true
  exit 1
fi
echo "user: listarr OK"

# 3. Scheduler worker init: reuse the production mechanism (gunicorn_config.py
#    post_fork sets SCHEDULER_WORKER on age==1) by creating the app directly
#    with that env set, and asserting the scheduler is running.
#    --user 1000: app deps were `pip install --user`-ed into
#    /home/listarr/.local at build time, so this must run as listarr (uid
#    1000), not the exec-default root, or `import flask` fails with
#    ModuleNotFoundError even though the app itself boots fine as listarr.
if ! docker exec -e SCHEDULER_WORKER=true --user 1000 "$NAME" python -c "
from listarr import create_app
from listarr.services import scheduler
app = create_app()
assert scheduler._scheduler is not None and scheduler._scheduler.running, 'scheduler not running'
print('scheduler: OK')"; then
  echo "scheduler: FAIL"
  docker logs "$NAME" || true
  exit 1
fi

# 4. ZoneInfo — prove the tzdata WHEEL works, not the Alpine apk package
#    (12-NOTES §6.2). Purge apk tzdata + all zoneinfo dirs first. This step
#    MUST run after steps 1-3 so an accidental reordering bug cannot make an
#    unrelated check fail because timezone data was already deleted.
#    The purge needs root (apk); the resolve-check needs --user 1000 (the
#    `tzdata` wheel lives under /home/listarr/.local, same reasoning as step 3)
#    — so this is two execs, not one.
if ! docker exec "$NAME" sh -c '
  rm -rf /usr/share/zoneinfo /usr/lib/zoneinfo /usr/share/lib/zoneinfo /etc/zoneinfo /usr/local/share/zoneinfo
  apk del --no-network tzdata 2>/dev/null || true'; then
  echo "zoneinfo: FAIL (purge step)"
  docker logs "$NAME" || true
  exit 1
fi
if ! docker exec --user 1000 "$NAME" python -c "
from zoneinfo import ZoneInfo
from datetime import datetime
z = ZoneInfo('America/New_York')
assert datetime(2026,1,1,tzinfo=z).utcoffset().total_seconds() == -5*3600
assert datetime(2026,7,1,tzinfo=z).utcoffset().total_seconds() == -4*3600
print('zoneinfo (pip tzdata only): OK')"; then
  echo "zoneinfo: FAIL (resolve step)"
  docker logs "$NAME" || true
  exit 1
fi

# 5. Fernet encrypt -> decrypt round-trip. Order-agnostic relative to step 4
#    (does not touch tzdata); kept last to group it with the other
#    credential-free proofs. --user 1000: same reasoning as step 3
#    (`cryptography` lives under /home/listarr/.local).
if ! docker exec --user 1000 "$NAME" python -c "
from cryptography.fernet import Fernet
k = Fernet.generate_key(); f = Fernet(k)
assert f.decrypt(f.encrypt(b'listarr-smoke')) == b'listarr-smoke'
print('fernet: OK')"; then
  echo "fernet: FAIL"
  docker logs "$NAME" || true
  exit 1
fi

echo "SMOKE PASS: $IMAGE"
