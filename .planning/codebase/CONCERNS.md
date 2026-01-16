# Codebase Concerns

**Analysis Date:** 2026-01-12

## Tech Debt

**Duplicate Code Between Radarr and Sonarr Services:**
- Issue: `listarr/services/radarr_service.py` and `listarr/services/sonarr_service.py` have nearly identical structure and functions
- Files: `listarr/services/dashboard_cache.py` (duplicate `_calculate_radarr_stats()` and `_calculate_sonarr_stats()` - 163 lines each)
- Why: Rapid prototyping during initial development
- Impact: Bug fixes must be duplicated, inconsistencies can emerge
- Fix approach: Create base service class or parameterized functions to handle both services

**Oversized Route File:**
- Issue: `listarr/routes/config_routes.py` is 592 lines, handling both Radarr and Sonarr configuration
- Files: `listarr/routes/config_routes.py`
- Why: Feature growth without refactoring
- Impact: Difficult to navigate, maintain, and test
- Fix approach: Split into `radarr_config_routes.py` and `sonarr_config_routes.py`, or extract shared logic

**Inefficient Dashboard Cache Calculation:**
- Issue: Fetches all lists into memory then filters in database with IN clause
- Files: `listarr/services/dashboard_cache.py:148-155` (Radarr), `listarr/services/dashboard_cache.py:260-266` (Sonarr)
- Why: Straightforward implementation without optimization
- Impact: Memory usage grows with number of lists
- Fix approach: Use single JOIN + GROUP BY query without loading all lists

## Known Bugs

**N+1 Query Pattern in Dashboard Recent Jobs:**
- Symptoms: One query fetches jobs, then 1-5 additional queries fetch list details
- Trigger: Loading dashboard page with recent jobs
- Files: `listarr/routes/dashboard_routes.py:82-104`
- Root cause: Fetching List objects in loop instead of eager loading
- Fix: Use SQLAlchemy `.joinedload()` or restructure query

**Missing HTTP Status Checks in Frontend:**
- Symptoms: JSON parse errors when API returns non-200 responses
- Trigger: Network errors or server errors during AJAX calls
- Files:
  - `listarr/static/js/config.js:133-134` (`fetchRadarrRootFolders()`)
  - `listarr/static/js/config.js:180-181` (`fetchRadarrQualityProfiles()`)
  - `listarr/static/js/config.js:275-276` (`fetchSonarrRootFolders()`)
  - `listarr/static/js/config.js:322-323` (`fetchSonarrQualityProfiles()`)
  - `listarr/static/js/config.js:361-362` (`loadSonarrSavedSettings()`)
  - `listarr/static/js/settings.js:49-56` (TMDB test)
- Root cause: Calling `.json()` without checking `response.ok` first
- Fix: Add `if (!response.ok) throw new Error(...)` before `.json()`

## Security Considerations

**Bare Exception Clauses Masking Errors:**
- Risk: Silent failures make debugging difficult, may hide security issues
- Files:
  - `listarr/routes/config_routes.py:29` (`_is_valid_url()`)
  - `listarr/services/radarr_service.py:27` (`validate_radarr_api_key()`)
  - `listarr/services/sonarr_service.py:27` (`validate_sonarr_api_key()`)
  - `listarr/services/tmdb_service.py:48` (`validate_tmdb_api_key()`)
- Current mitigation: None (catches all exceptions silently)
- Recommendations: Catch specific exceptions (`requests.RequestException`, `ConnectionError`, `Timeout`) and log actual errors

**Missing Input Validation on Import Settings:**
- Risk: Invalid IDs could be stored, causing silent failures during import
- Files:
  - `listarr/routes/config_routes.py:392` (`save_radarr_import_settings()`)
  - `listarr/routes/config_routes.py:542` (`save_sonarr_import_settings()`)
  - Lines 414, 568 convert IDs without validation
- Current mitigation: None
- Recommendations: Validate IDs against actual Radarr/Sonarr configuration before saving

**Default Secret Key in Development:**
- Risk: Development default secret key could be accidentally deployed
- Files: `listarr/__init__.py:15`
- Current mitigation: `.env.example` warns about this
- Recommendations: Raise error if SECRET_KEY is not set when FLASK_ENV is production

## Performance Bottlenecks

**Dashboard Cache Refresh:**
- Problem: Synchronous cache refresh blocks request
- Files: `listarr/routes/dashboard_routes.py:67-77`, `listarr/services/dashboard_cache.py:148-266`
- Measurement: Not measured, but could be slow with many services/jobs
- Cause: Sequential API calls to Radarr, Sonarr, database queries
- Improvement path: Use async/await or background task queue (Celery commented out in requirements.txt)

**No Database Indexing Strategy:**
- Problem: No explicit indexes defined beyond primary keys
- Files: `listarr/models/*.py`
- Measurement: Not measured
- Cause: Small dataset size doesn't require indexes yet
- Improvement path: Add indexes on foreign keys and frequently queried fields (e.g., `is_active`, `target_service`)

## Fragile Areas

**Thread-Safe Cache Partially Protected:**
- Why fragile: Lock only protects cache assignment, not partial reads during calculation
- Files: `listarr/services/dashboard_cache.py:50` (lock definition), `listarr/services/dashboard_cache.py:308-309` (read without lock)
- Common failures: Stale cache data during refresh
- Safe modification: Acquire lock for all cache reads and writes
- Test coverage: Tested via integration tests but not thread-safety specific tests

**Encryption Key Loading Logic:**
- Why fragile: Multiple fallback paths (env var → file → generate)
- Files: `listarr/services/crypto_utils.py:94-107`
- Common failures: Key file deleted or corrupted
- Safe modification: Always validate key format before using
- Test coverage: Unit tests cover key generation and loading

## Scaling Limits

**In-Memory Cache:**
- Current capacity: Limited by available RAM
- Limit: No limit enforced, grows with number of services
- Symptoms at limit: High memory usage, potential OOM
- Scaling path: Use Redis or memcached for distributed caching

**SQLite Database:**
- Current capacity: Suitable for small-to-medium deployments
- Limit: Concurrency limitations, no distributed support
- Symptoms at limit: Database locked errors under high write load
- Scaling path: Migrate to PostgreSQL or MySQL for production

## Dependencies at Risk

**Loose Version Constraints:**
- Risk: `pyarr>=5.0.0` could install incompatible future versions
- Files: `requirements.txt`
- Impact: Breaking changes in pyarr could break Radarr/Sonarr integrations
- Migration plan: Pin to specific versions or use version ranges (e.g., `pyarr>=5.0.0,<6.0.0`)

**Potential Outdated Dependencies:**
- Risk: Dependencies may have security vulnerabilities
- Files: `requirements.txt`
- Impact: Security vulnerabilities, compatibility issues
- Migration plan: Run `pip-audit` or `safety check` to identify vulnerabilities

## Missing Critical Features

**No Background Task Queue:**
- Problem: All operations are synchronous, no scheduled jobs
- Current workaround: Manual triggering via UI
- Blocks: Automated list imports on schedule
- Implementation complexity: Medium (Celery + Redis commented out in requirements.txt)

**No API Rate Limiting:**
- Problem: No protection against API abuse or rapid requests
- Current workaround: None
- Blocks: Production deployment at scale
- Implementation complexity: Low (Flask-Limiter extension)

**No User Authentication:**
- Problem: No login system, anyone with access can use the app
- Current workaround: Deploy behind VPN or firewall
- Blocks: Multi-user deployments
- Implementation complexity: Medium (Flask-Login + password hashing)

## Test Coverage Gaps

**Integration Tests for Complete Workflows:**
- What's not tested: Full API key save → encrypt → decrypt → use in API call workflow
- Files: Integration tests exist but not comprehensive
- Risk: Regressions in core encryption/decryption functionality
- Priority: High
- Difficulty to test: Low (fixtures already exist)

**Error Handling in Dashboard Cache:**
- What's not tested: Cache refresh when services are offline or returning errors
- Files: `listarr/services/dashboard_cache.py`
- Risk: Cache could get stuck in invalid state
- Priority: Medium
- Difficulty to test: Medium (need to mock service failures)

---

*Concerns audit: 2026-01-12*
*Update as issues are fixed or new ones discovered*
