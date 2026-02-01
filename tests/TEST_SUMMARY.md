# Listarr Test Suite Summary

**Last Updated:** 2026-02-01
**Total Tests:** 444 tests
**Pass Rate:** 100% (all tests passing)
**Overall Coverage:** 56%

## Overview

Comprehensive test suite covering unit tests, integration tests, and route tests for the Listarr application. This suite has grown from 415 tests (52% coverage baseline) to 444 tests (56% coverage) through Phase 6.3 test generation efforts.

## Test Distribution

### Test Files by Category

| Category | Test File | Test Count | Coverage Areas |
|----------|-----------|------------|----------------|
| **Unit Tests** | | | |
| Crypto utilities | `unit/test_crypto_utils.py` | 30 tests | Key generation, encryption/decryption, error handling |
| TMDB service | `unit/test_tmdb_service.py` | 47 tests | API validation, trending, popular, discover, top_rated, IMDB mapping |
| TMDB cache | `unit/test_tmdb_cache.py` | 15 tests | Cached TMDB functions, region filtering, cache keys |
| Radarr service | `unit/test_radarr_service.py` | 26 tests | API validation, quality profiles, root folders, system status |
| Sonarr service | `unit/test_sonarr_service.py` | 29 tests | API validation, quality profiles, root folders, system status |
| Service config model | `unit/test_service_config_model.py` | 18 tests | Model fields, constraints, CRUD operations |
| Job executor | `unit/services/test_job_executor.py` | 13 tests | Job submission, status tracking, lifecycle |
| **Integration Tests** | | | |
| Settings integration | `integration/test_settings_integration.py` | 18 tests | End-to-end workflows, database operations, error recovery |
| Config integration | `integration/test_config_integration.py` | 22 tests | Radarr/Sonarr workflows, encryption, database operations |
| Dashboard integration | `integration/test_dashboard_integration.py` | 18 tests | End-to-end workflows, cache refresh, multi-service scenarios |
| Import integration | `integration/test_import_integration.py` | 7 tests | Top rated import handling, multi-page fetching |
| **Route Tests** | | | |
| Settings routes | `routes/test_settings_routes.py` | 35 tests | GET/POST endpoints, AJAX testing, CSRF protection |
| Config routes | `routes/test_config_routes.py` | 140 tests | Radarr/Sonarr config, quality profiles, root folders, import settings |
| Dashboard routes | `routes/test_dashboard_routes.py` | 38 tests | Page rendering, stats API, recent jobs API |
| Jobs routes | `routes/test_jobs_routes.py` | 20 tests | Jobs listing, filtering, detail, rerun, clear |
| Lists routes | `routes/test_lists_routes.py` | 8 tests | Import triggers, status polling |

**Total:** 444 tests

## Phase 6.2 Test Coverage (Added in Phase 6.3)

**Added:** 2026-02-01
**Tests Added:** 29 new tests across Plans 02 and 03
**Coverage Improvement:** +4% overall (52% → 56%)

### Coverage Areas

#### tmdb_service.py (Top Rated Functions)
- **TestGetTopRatedMovies:** 4 tests
  - Returns results with valid API key
  - Handles empty API key gracefully
  - Handles exceptions properly
  - Supports pagination
- **TestGetTopRatedTV:** 4 tests
  - Returns results with valid API key
  - Handles empty API key gracefully
  - Handles exceptions properly
  - Supports pagination

**Coverage:** 71% → 83% (+12%)

#### tmdb_cache.py (Caching Layer)
- **TestGetTopRatedMoviesCached:** 4 tests
  - Returns results on cache miss
  - Returns cached results on second call
  - Different pages have separate cache keys
  - Returns empty list on API error
- **TestGetTopRatedTVCached:** 3 tests
  - Returns results on cache miss
  - Returns cached results on second call
  - Different pages have separate cache keys
- **TestGetTMDBRegion:** 4 tests
  - Returns configured region
  - Returns None when region not configured
  - Returns None when no TMDB config exists
  - Preserves region code case
- **TestRegionAwareCacheKeys:** 3 tests
  - Different regions use different cache keys
  - Same region reuses cached result
  - No region uses worldwide cache key

**Coverage:** 14% → 40% (+26%)

#### import_service.py (Top Rated Import)
- **TestFetchTMDBItemsTopRated:** 5 tests
  - Fetches top rated movies using cached function
  - Fetches top rated TV using cached function
  - Limit parameter controls item count
  - Handles empty response gracefully
  - Handles API errors gracefully
- **TestFetchTMDBItemsLimitBehavior:** 2 tests
  - Stops fetching when page returns less than 20
  - Respects limit across multiple pages

**Coverage:** 9% → 22% (+13%)

## Test Quality Metrics

### Coverage by Module Type

| Module Type | Coverage | Notes |
|-------------|----------|-------|
| Models | 95%+ | Comprehensive CRUD and constraint testing |
| Services (Core) | 75%+ | Crypto, TMDB, Radarr, Sonarr well-covered |
| Services (Phase 6.2) | 40%+ | New Phase 6.2 modules have dedicated tests |
| Routes (Settings/Config) | 85%+ | High coverage for critical configuration paths |
| Routes (Dashboard/Jobs) | 80%+ | Good coverage for monitoring and job management |
| Routes (Lists) | 16% | Minimal coverage (future improvement target) |

### Test Categories

- **Unit tests:** 178 tests (40%)
- **Integration tests:** 65 tests (15%)
- **Route tests:** 201 tests (45%)

### Critical Path Coverage

- **Authentication & Encryption:** >95%
- **TMDB API Integration:** >80%
- **Radarr/Sonarr Integration:** >85%
- **Dashboard Metrics:** >85%
- **Job Execution:** >35% (basic coverage)

## Running Tests

See [tests/README.md](./README.md) for detailed instructions on:
- Installing test dependencies
- Running specific test categories
- Generating coverage reports
- Writing new tests

## Continuous Improvement

### Next Phase Priorities

1. **Lists Routes:** Currently at 16% coverage - needs comprehensive test suite
2. **Job Executor:** At 35% coverage - add more lifecycle and error handling tests
3. **Dashboard Cache:** At 64% coverage - test edge cases and concurrency scenarios

### Test Generation Strategy

Phase 6.3 successfully demonstrated a systematic approach to test generation:
1. Establish coverage baseline
2. Identify gap priorities based on code criticality
3. Generate tests in dependency order (service → cache → import → routes)
4. Target 90%+ coverage for customer-facing Phase 6.2 modules
5. Verify improvement with final coverage analysis

---

**Maintained by:** Listarr Development Team
**Coverage Tool:** pytest-cov with branch coverage enabled
**Test Framework:** pytest 7.4.3 with pytest-flask and pytest-mock
