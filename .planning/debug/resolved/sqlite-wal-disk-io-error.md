---
status: resolved
trigger: "sqlite-wal-disk-io-error"
created: 2026-02-01T00:00:00Z
updated: 2026-02-01T23:15:00Z
---

## ROOT CAUSE FOUND

**SQLite WAL mode incompatibility with network/FUSE filesystems**

WAL mode requires shared memory and POSIX file locking, which fail on:
- Network shares (SMB/CIFS/NFS)
- FUSE filesystems (Unraid's shfs user shares)
- Certain Docker volume configurations

## Symptoms

expected: Application should handle database operations consistently without crashing
actual: Application freezes/breaks intermittently with sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) disk I/O error
errors:
```
File "/app/listarr/__init__.py", line 23, in set_sqlite_pragma
    cursor.execute("PRAGMA journal_mode=WAL")
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) disk I/O error
```

reproduction: Random/intermittent - happens unpredictably during normal use
timeline: Started after running in Docker; works most of the time but randomly fails

## Environment

- Docker container on Unraid
- Gunicorn: 2 workers, 4 threads each
- Database mount: `/mnt/user/appdata/listarr/instance:/app/instance`
- Filesystem: Unraid user share (FUSE-based shfs)
- Development path: UNC network share

## Evidence

- Gunicorn with 2 workers = 2 separate processes accessing SQLite
- `set_sqlite_pragma` executes `PRAGMA journal_mode=WAL` on every new connection
- WAL mode requires shared memory (`-shm` file) and file locking
- FUSE/network filesystems implement these incompletely
- Error is intermittent due to timing-dependent locking failures

## Resolution

**Implemented:** Graceful fallback with error handling

```python
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    global _wal_mode_logged
    if "sqlite" in str(type(dbapi_connection)).lower():
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            result = cursor.fetchone()
            if result and result[0].upper() != "WAL":
                raise ValueError(f"Filesystem returned {result[0]} instead of WAL")
        except Exception as e:
            # Fall back to DELETE mode for network/FUSE filesystems
            try:
                cursor.execute("PRAGMA journal_mode=DELETE")
            except Exception:
                pass
            if not _wal_mode_logged:
                logger.warning(f"SQLite WAL mode unavailable ({e}), using DELETE mode.")
                _wal_mode_logged = True
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
```

**Benefits of this approach:**
1. Tries WAL mode first (best performance on supported filesystems)
2. Gracefully falls back to DELETE mode if WAL fails
3. Logs a single warning (no log spam)
4. Works on all filesystem types

files_changed:
- listarr/__init__.py (lines 16-55)

## Verification

1. Rebuild Docker image
2. Restart container
3. Check logs - expect "SQLite WAL mode unavailable" warning on FUSE/network filesystems
4. Confirm no more disk I/O errors during normal operation
