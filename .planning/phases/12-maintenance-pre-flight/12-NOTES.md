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

_(pending)_

### Gate Results

_(pending)_

### Baseline coverage TOTAL

_(pending)_

---

## 2. Dependency Review Table

_Current-vs-latest pin review for APScheduler, SQLAlchemy, Flask-SQLAlchemy, cronsim,
cron-descriptor, tzdata (and a cryptography row per D-16). Markdown table with columns
`Package | Current pin | Latest | Checked | Action | Changelog summary`. Filled by plan 12-02._

D-09 rationale (recorded in writing): the `<4` / `<2.1` language in success criterion 2 is
*rationale* — "don't chase majors" — not a specification for the pin operator. This file keeps
exact `==` pins for all runtime dependencies, matching the existing `requirements.txt`
convention. No range operators are introduced.

_(pending)_

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

_(none so far)_

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
