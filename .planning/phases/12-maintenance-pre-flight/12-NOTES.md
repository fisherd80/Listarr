# Phase 12 — Maintenance Pre-flight — Evidence Notes

**Started:** 2026-09-02

This is the Phase 12 evidence artifact (D-05). All clean-state evidence — commands,
current-vs-latest version table, output snippets, dates, changelog summaries, and any
non-mechanical fixes — accumulates here during execution and feeds the eventual phase SUMMARY.

---

## 1. Pre-change Baseline

_Coverage TOTAL % on an untouched tree plus a verbatim snapshot of all five quality gates
(pip-audit, ruff check, ruff format --check, pytest, bandit). Populated by Task 2 of plan 12-01._

### Environment

| Property | Value |
|----------|-------|
| Recorded | 2026-09-02 (UTC) |
| Git short SHA | `9e89849` (tree state: `requirements.txt`, `Dockerfile`, `tests/` all untouched — confirmed `git status --porcelain requirements.txt Dockerfile tests/` empty before measuring) |
| Python | `Python 3.14.3` (`python -V`) |
| pip | `pip 26.1.1 from C:\Program Files\Python314\Lib\site-packages\pip (python 3.14)` |
| Platform | `Windows-11-10.0.26200-SP0` (`platform.platform()`) |
| Test env | Host global interpreter (`C:\Program Files\Python314\python.exe`), not a project venv |

> **Interpreter note (recorded honestly, not a Phase 12 change):** the planning docs
> (12-CONTEXT / 12-RESEARCH) assume a Python 3.11 project venv. The baseline above was
> taken on the host global **Python 3.14.3** install, which is what is available on this
> machine. Consequences for downstream comparison:
> - Bare `pip-audit` (no `-r`) scans the whole global site-packages and therefore reports
>   35 findings across 6 packages (`pillow`, `pypdf`, `pip`, `click`, `msgpack`, `cryptography`) —
>   only the 5 `cryptography` rows are Listarr runtime dependencies. The lockfile-scoped
>   `pip-audit -r requirements.txt` (5 findings, 1 package) is the **finding of record** for
>   this project and is the number plan 12-03 must clear.
> - The coverage TOTAL below (73.29%) was produced by CPython 3.14. Plan 12-06's Docker
>   proof runs on `python:3.11-alpine`; a small interpreter-driven delta is possible.
>   D-04's intent is "a drop is a red flag that a bump disabled a code path" — evaluate
>   the 12-06 number against 73.29% with that intent, allowing for the interpreter change.

### Gate Results

Pre-change state of all five quality gates, measured on the tree at commit `9e89849`
(no Phase 12 edits to `requirements.txt` / `Dockerfile` / `tests/`):

| Gate | Command | Exit code | Result |
|------|---------|-----------|--------|
| Dependency audit | `pip-audit` (bare, global env) | 1 | RED — 35 findings / 6 pkgs; only 5 `cryptography==46.0.7` rows are Listarr deps (rest are unrelated global packages) |
| Dependency audit | `pip-audit -r requirements.txt` (lockfile, finding of record) | 1 | RED (expected — resolved by plan 12-03 per D-16/D-12) — 5 findings in 1 package: `cryptography==46.0.7` |
| Lint | `ruff check .` | 0 | GREEN — `All checks passed!` |
| Format | `ruff format --check .` | 0 | GREEN — `56 files already formatted` |
| Test suite + coverage | `pytest --cov=listarr --cov-report=term-missing` | 0 | GREEN — `599 passed in 175.15s`, `TOTAL` coverage `73.29%` |
| Security scan | `bandit -r listarr -ll` | 0 | GREEN — `No issues identified.` (1 Low-severity item exists but is below the `-ll` medium threshold) |

Only `pip-audit` is RED, exactly as anticipated by D-16. `ruff`, `pytest`, and `bandit`
are all green — the phase starts from the expected clean state and no pre-existing
non-`pip-audit` baseline failure needs to be surfaced.

#### `pip-audit` — verbatim output (finding of record: `pip-audit -r requirements.txt`)

```
$ pip-audit -r requirements.txt
Found 5 known vulnerabilities in 1 package
Name         Version ID                  Fix Versions
------------ ------- ------------------- ------------
cryptography 46.0.7  PYSEC-2026-3554     49.0.0
cryptography 46.0.7  PYSEC-2026-3552     50.0.0
cryptography 46.0.7  PYSEC-2026-3553     49.0.0
cryptography 46.0.7  PYSEC-2026-3554     49.0.0
cryptography 46.0.7  GHSA-537c-gmf6-5ccf 48.0.1
EXIT=1
```

Findings of record: **PYSEC-2026-3552** (fixed in `cryptography==50.0.0`), PYSEC-2026-3553
(fixed in 49.0.0), PYSEC-2026-3554 (fixed in 49.0.0, listed twice), GHSA-537c-gmf6-5ccf
(fixed in 48.0.1). Only `cryptography==50.0.1` clears all five (per D-16). **Not fixed in
this plan** — plan 12-03 pins `cryptography==50.0.1` and validates with `pytest -m encryption`.
The non-zero exit here is expected and is NOT a task failure.

#### `pip-audit` — verbatim output (bare, whole global environment)

```
$ pip-audit
Found 35 known vulnerabilities in 6 packages
Name         Version ID                  Fix Versions
------------ ------- ------------------- ------------
click        8.3.2   PYSEC-2026-2132     8.3.3
cryptography 46.0.7  PYSEC-2026-3554     49.0.0
cryptography 46.0.7  PYSEC-2026-3552     50.0.0
cryptography 46.0.7  PYSEC-2026-3553     49.0.0
cryptography 46.0.7  PYSEC-2026-3554     49.0.0
cryptography 46.0.7  GHSA-537c-gmf6-5ccf 48.0.1
msgpack      1.1.2   PYSEC-2026-3625     1.2.1
pillow       12.2.0  PYSEC-2026-2253     12.3.0
pillow       12.2.0  PYSEC-2026-2255     12.3.0
pillow       12.2.0  PYSEC-2026-2257     12.3.0
pillow       12.2.0  PYSEC-2026-2256     12.3.0
pillow       12.2.0  PYSEC-2026-2254     12.3.0
pillow       12.2.0  PYSEC-2026-3453     12.3.0
pillow       12.2.0  PYSEC-2026-3451     12.3.0
pillow       12.2.0  PYSEC-2026-3452     12.3.0
pillow       12.2.0  PYSEC-2026-2254     12.3.0
pillow       12.2.0  PYSEC-2026-2253     12.3.0
pillow       12.2.0  PYSEC-2026-2256     12.3.0
pillow       12.2.0  PYSEC-2026-2255     12.3.0
pillow       12.2.0  PYSEC-2026-3451     12.3.0
pillow       12.2.0  PYSEC-2026-3452     12.3.0
pillow       12.2.0  PYSEC-2026-3453     12.3.0
pillow       12.2.0  PYSEC-2026-3454     12.3.0
pillow       12.2.0  PYSEC-2026-3495     12.3.0
pillow       12.2.0  PYSEC-2026-3496     12.3.0
pillow       12.2.0  PYSEC-2026-3494     12.3.0
pillow       12.2.0  PYSEC-2026-3493     12.3.0
pip          26.1.1  PYSEC-2026-196      26.1.2
pip          26.1.1  PYSEC-2026-196      26.1.2
pip          26.1.1  PYSEC-2026-3721     26.2
pypdf        6.14.2  PYSEC-2026-3655     6.15.0
pypdf        6.14.2  PYSEC-2026-3656     6.15.0
pypdf        6.14.2  CVE-2026-84309      6.16.0
pypdf        6.14.2  CVE-2026-84310      6.16.1
pypdf        6.14.2  CVE-2026-84311      6.16.1
EXIT=1
```

`click`, `msgpack`, `pillow`, `pypdf`, `pip` are **not** in `requirements.txt` — they are
pre-existing packages in the shared host interpreter and out of scope for Phase 12
(and for Listarr entirely). The lockfile-scoped scan above is the authoritative baseline.

#### `ruff` / `bandit` — output excerpts

```
$ ruff check .
All checks passed!
EXIT=0

$ ruff format --check .
56 files already formatted
EXIT=0

$ bandit -r listarr -ll
Test results:
	No issues identified.
Code scanned:
	Total lines of code: 4812
Run metrics:
	Total issues (by severity): Low: 1, Medium: 0, High: 0
EXIT=0
```

#### `pytest --cov=listarr` — summary + TOTAL line

```
$ pytest --cov=listarr --cov-report=term-missing
...
Name                                     Stmts   Miss   Cover   Missing
-----------------------------------------------------------------------
TOTAL                                     2894    773  73.29%
======================= 599 passed in 175.15s (0:02:55) =======================
EXIT=0
```

### Baseline coverage TOTAL

Baseline coverage TOTAL: 73.29% (recorded 2026-09-02, commit 9e89849)

This is the D-04 comparison target. Plan 12-06 re-runs `pytest --cov=listarr` and asserts
the fresh `TOTAL` is `>= 73.29%` and `>= 60%` (criterion 5, non-negative delta). Phase 12
changes zero application code, so any drop below 73.29% signals a dependency bump silently
disabled a code path (subject to the interpreter-change caveat in the Environment note above).

---

## 2. Dependency Review Table

_Current-vs-latest pin review for APScheduler, SQLAlchemy, Flask-SQLAlchemy, cronsim,
cron-descriptor, tzdata (and a cryptography row per D-16). Markdown table with columns
`Package | Current pin | Latest | Checked | Action | Changelog summary`. Filled by plan 12-02._

D-09 rationale (recorded in writing): the `<4` / `<2.1` language in success criterion 2 is
*rationale* — "don't chase majors" — not a specification for the pin operator. This file keeps
exact `==` pins for all runtime dependencies, matching the existing `requirements.txt`
convention. No range operators are introduced.

### Review table

| Package | Pre-Phase-12 pin | Latest | Checked | Action | Changelog summary |
|---------|------------------|--------|---------|--------|-------------------|
| APScheduler | `==3.11.2` | `3.11.3` | 2026-09-02 | bumped | `3.11.3` is exactly two bug fixes over `3.11.2`: a DST spring-forward correction for sub-minute `IntervalTrigger` jobs evaluated under `ZoneInfo`, and a fix for imported-job store links. Neither touches this codebase's APScheduler surface — `BackgroundScheduler(timezone=<str>)`, `job_defaults`, `CronTrigger.from_crontab`, `job.next_run_time`. Listarr registers only cron triggers (no `IntervalTrigger`) and runs the default `MemoryJobStore` (no imported/persisted jobs), so both fixes are inert here. Stays in the `3.11.x` line, far below the `4.x` rewrite. Verified against the GitHub release notes. |
| SQLAlchemy | `==2.0.46` | `2.0.52` | 2026-09-02 | bumped | The crossed range `2.0.47`–`2.0.52` contains no change to `TypeDecorator`, `cache_ok`, `DateTime` result processing, or the legacy `Query.get()` API — the surfaces `listarr/models/custom_types.py:TZDateTime` and the ~69 legacy call sites depend on. The range is bug fixes plus added Python 3.14/3.15 support. `TZDateTime.cache_ok = True` stays valid: the compiled-cache key contract for `TypeDecorator` is unchanged across the range. Stays in the `2.0.x` line, below the `2.1` boundary. Verified against the official `changelog_20.html`. |
| Flask-SQLAlchemy | `==3.1.1` | `3.1.1` | 2026-09-02 | already current — no bump | `3.1.1` is the newest release on PyPI as of the checked date. Its requirement floor (`flask>=2.2.5`, `sqlalchemy>=2.0.16`) is satisfied by `Flask==3.1.3` and the bumped `SQLAlchemy==2.0.52`. Reviewed no-op per D-10 — no newer version exists to cross. |
| cronsim | `==2.7` | `2.7` | 2026-09-02 | already current — no bump | `2.7` (released 2025-10-21) is the newest release on PyPI as of the checked date. `requires_python >=3.10` is compatible with the `py311` target. Feeds `validate_cron_expression()` / `get_next_run_time()`; no newer version exists to review. Reviewed no-op per D-10. |
| cron-descriptor | `==2.0.6` | `2.1.0` | 2026-09-02 | bumped | `2.1.0` (2026-06-02) is a minor/feature release. The one packaging-relevant change is a new **`typing_extensions`** runtime dependency that `2.0.6` did not declare — pure-Python, python-core maintained, resolved as `typing_extensions==4.15.0` in this environment. Recorded here so the Phase 15 pin sweep treats it as accounted-for rather than a mystery dependency (Pitfall 6). The consumed surface — `get_description()` inside `validate_cron_expression()` — is unchanged; descriptions for the cron expressions Listarr generates are unaffected. |
| tzdata | *(absent)* | `2026.3` | 2026-09-02 | added | Added `tzdata==2026.3` to the `# Scheduler` block under an explanatory comment. Supplies the IANA tz database to `zoneinfo.ZoneInfo(...)` when the system `TZPATH` is empty (Alpine musl) or absent (Windows). `tzdata` is a rolling `YYYY.n` data release, so the exact `==` pin (required by D-09 / D-10b — no ranges) will need manual bumps in future maintenance phases as IANA publishes new rules. Referenced by the CPython `zoneinfo` docs as the first-party fallback data source. |

_The `cryptography` row is intentionally omitted here — plan 12-03 adds it under D-16._

### Verification posture (D-02)

The fast inner loop for iterating on these bumps is a throwaway host venv
(`python -m venv` + `pip install -r requirements.txt`); `ruff`, `pytest`, and `bandit`
are not runtime-environment-sensitive so a host run is a valid signal for them. It is **not**
the authoritative proof. Per D-01 the authoritative fresh-install proof — a clean `pip install`
against a musl base with no system `/usr/share/zoneinfo`, plus `pip-audit`, the
`ZoneInfo('America/New_York')` assertion, and full `pytest` — is the Docker image build in
plan 12-06, not this host. The host here is Python 3.14.3 and already carries a `tzdata`
package, so a local `zoneinfo` check false-greens; only the 12-06 container run is decisive.

For this plan's changes specifically: after the Task 2 bumps, `pip install -r requirements.txt`
succeeded, the full suite ran `599 passed` with coverage `TOTAL 73.29%` (identical to the
section 1 baseline), and `ruff check .` / `ruff format --check .` / `bandit -r listarr -ll`
were all green. No test broke, so no non-mechanical change was required (see section 5).

---

## 3. Deprecation Canary (Phase 14/15 hand-off)

_Full list of deprecation sites from `pytest -W always::DeprecationWarning -W always::PendingDeprecationWarning -rw`
run against the bumped stack — the ~69 legacy `.query.get()` call sites, any `datetime.utcnow()`,
any `MovedIn20Warning` / `LegacyAPIWarning` / APScheduler 3.11 warnings — recorded as a
work-list hand-off for Phases 14–15. Zero code changes in Phase 12. Filled by plan 12-05._

_(pending)_

---

## 4. pip-audit Findings and Resolution

_Each `pip-audit` finding plus its resolution path (bump/pin to a fixed version, or a justified
`--ignore-vuln` allowlist entry with a tracking issue link). Phase 12 must be actually green,
not green-by-deferral (D-12). Filled by plan 12-03._

_(pending)_

---

## 5. Non-mechanical Change Log (D-13a)

_Every behaviour-adjacent fix made anywhere in Phase 12 gets one line here: what broke, what
changed, why it is behaviour-preserving. An empty log is distinguishable from an unfilled one
by the explicit marker below._

- **Plan 12-02 (tzdata add + scheduler/ORM bumps):** no non-mechanical changes required. The
  `tzdata==2026.3` add and the `SQLAlchemy 2.0.46→2.0.52` / `APScheduler 3.11.2→3.11.3` /
  `cron-descriptor 2.0.6→2.1.0` bumps were purely mechanical pin edits; the full suite stayed
  `599 passed` at `73.29%` coverage with no test or call-site touched.

---

## 6. Docker Image Proof (D-01)

_Transcript of the authoritative fresh-install proof: build the image from the `Dockerfile`
(base tag corrected per D-17), then run `pip-audit`, the
`python -c "from zoneinfo import ZoneInfo; ZoneInfo('America/New_York')"` assertion, and full
`pytest` inside the container. Filled by plan 12-06._

_(pending)_

---

## 7. Coverage Delta (D-04 / criterion 5)

_Final coverage-delta line: a fresh `pytest --cov=listarr` TOTAL % compared against the
`### Baseline coverage TOTAL` number recorded in section 1. Must be `>= baseline` and `>= 60%`.
Filled by plan 12-06._

_(pending)_
