# External Integrations

**Analysis Date:** 2026-01-12

## APIs & External Services

**TMDB (The Movie Database):**
- TMDB API - Content discovery (trending, popular, discover movies/TV)
  - SDK/Client: tmdbv3api >= 1.9.0 npm package
  - Auth: API key configured via settings page, encrypted in database
  - Endpoints used: trending, popular, discover, movie/TV details, IMDB ID mapping
  - Configuration: `listarr/models/service_config_model.py` (ServiceConfig table)
  - Service: `listarr/services/tmdb_service.py`

**Radarr (Movie Management):**
- Radarr API - Movie library automation
  - SDK/Client: pyarr >= 5.0.0
  - Auth: Base URL + API Key configured on `/config` route
  - Endpoints used: system/status, quality profiles, root folders, movie counts, missing movies
  - Configuration: `listarr/routes/config_routes.py`, `listarr/models/service_config_model.py`
  - Import Settings: `listarr/models/service_config_model.py` (MediaImportSettings table)
  - Service: `listarr/services/radarr_service.py`
  - Dashboard Stats: Cached statistics via `listarr/services/dashboard_cache.py`

**Sonarr (TV Management):**
- Sonarr API - TV series library automation
  - SDK/Client: pyarr >= 5.0.0
  - Auth: Base URL + API Key configured on `/config` route
  - Endpoints used: system/status, quality profiles, root folders, series counts, missing episodes
  - Configuration: `listarr/routes/config_routes.py`, `listarr/models/service_config_model.py`
  - Import Settings: `listarr/models/service_config_model.py` (MediaImportSettings table)
  - Service: `listarr/services/sonarr_service.py`
  - Dashboard Stats: Cached statistics via `listarr/services/dashboard_cache.py`

## Data Storage

**Databases:**
- SQLite (embedded) - Primary data store
  - Connection: No external DB required, file-based at `instance/listarr.db`
  - Client: SQLAlchemy 2.0.23 ORM
  - Migrations: Manual (no migration framework detected)
  - Persistence: Docker volume `listarr-data:/app/instance`

**File Storage:**
- Local filesystem - Configuration and runtime data
  - Encryption key: `instance/.fernet_key`
  - Database: `instance/listarr.db`
  - Location: Mounted via Docker volume in production

**Caching:**
- In-memory cache - Dashboard statistics
  - Implementation: Python dict with threading.Lock for thread safety
  - Service: `listarr/services/dashboard_cache.py`
  - Refresh: On startup and on-demand via `/api/dashboard/stats?refresh=true`

## Authentication & Identity

**Auth Provider:**
- Flask session-based authentication - Built-in Flask sessions
  - Implementation: Flask SECRET_KEY based sessions
  - Token storage: Server-side sessions (Flask default)
  - Session management: Flask session cookies

**API Key Management:**
- Fernet symmetric encryption - Stored API keys encrypted at rest
  - Credentials: API keys encrypted using Fernet (`listarr/services/crypto_utils.py`)
  - Storage: ServiceConfig model with encrypted fields
  - Key location: `instance/.fernet_key` or `FERNET_KEY` env var

## Monitoring & Observability

**Error Tracking:**
- Flask logging - Built-in Python logging
  - Configuration: `current_app.logger`
  - Levels: DEBUG, INFO, WARNING, ERROR
  - Output: stdout/stderr (captured by Docker)

**Analytics:**
- None detected

**Logs:**
- Docker logs - stdout/stderr only
  - Integration: Docker log driver (default json-file)
  - Retention: Depends on Docker configuration

## CI/CD & Deployment

**Hosting:**
- Docker containerized deployment
  - Deployment: Manual via docker-compose or container orchestration
  - Environment vars: Configured via .env file or Docker environment

**CI Pipeline:**
- None detected in repository
  - Tests can be run via pytest
  - No GitHub Actions or GitLab CI configuration found

## Environment Configuration

**Development:**
- Required env vars: None (defaults work for development)
- Secrets location: `.env` file (gitignored)
- Mock/stub services: Use real TMDB/Radarr/Sonarr test instances or mocks in tests

**Staging:**
- Not explicitly configured
- Could use separate .env file with staging API keys

**Production:**
- Secrets management: Environment variables via Docker or .env file
- Encryption key: `instance/.fernet_key` persisted in Docker volume
- Database: `instance/listarr.db` persisted in Docker volume

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

---

*Integration audit: 2026-01-12*
*Update when adding/removing external services*
