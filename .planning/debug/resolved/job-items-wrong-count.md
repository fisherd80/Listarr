---
status: resolved
trigger: "Job detail expansion in Jobs page UI shows more items than actually belong to that job. Database confirms the mismatch - job_items table has 120 rows for a job that should only have 20 items."
created: 2026-01-30T12:00:00Z
updated: 2026-01-30T12:00:00Z
---

## Current Focus

hypothesis: JobItem cascade delete not working - when jobs are cleared, JobItems persist. New jobs reuse old IDs and appear to have accumulated items.
test: Check JobItem foreign key cascade configuration in jobs_model.py
expecting: Missing ON DELETE CASCADE or relationship cascade setting
next_action: Examine JobItem model foreign key definition

## Symptoms

expected: When expanding a job row on the Jobs page, should show only the items that belong to that specific job (e.g., 20 items for a list with 20-item limit)
actual: Job expansion shows 120 items instead of 20. Database query on job_items table for that job_id also returns 120 rows, suggesting items are being stored incorrectly (accumulating across runs)
errors: No explicit errors - just wrong data
reproduction: Run the same list twice (e.g., list 5). First run shows correct 20 items. Second run a few minutes later shows 120 rows in the expansion AND in the database.
started: Discovered during Phase 6 UAT verification

## Eliminated

## Evidence

- timestamp: 2026-01-30T12:05:00Z
  checked: Database state - jobs vs job_items
  found: |
    - jobs table has 3 records (IDs 1, 2, 3)
    - job_items table has entries for job_ids 1, 2, 3, 4, 5, 6
    - job_id=3 has 120 items but job record shows items_found=20
    - job_ids 4, 5, 6 have no corresponding job records
    - Total job_items: 340 across 6 job_ids
  implication: Jobs were cleared/deleted but JobItems persisted. When new jobs were created, they reused IDs 1, 2, 3 and got mixed with orphaned items from old jobs

- timestamp: 2026-01-30T12:08:00Z
  checked: JobItem foreign key definition in jobs_model.py line 53
  found: |
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    - No ondelete="CASCADE" specified
    - No relationship defined on Job model with cascade delete
  implication: CONFIRMED - Foreign key lacks cascade delete. When jobs are deleted, JobItems are orphaned

- timestamp: 2026-01-30T12:09:00Z
  checked: clear_all_jobs in jobs_routes.py lines 163-185
  found: |
    Uses bulk delete: Job.query.filter(...).delete(synchronize_session=False)
    Comment says "cascade should handle this" but cascade isn't configured
    Bulk delete bypasses ORM relationships even if they existed
  implication: Even with ORM cascade, bulk delete would skip it. Need database-level CASCADE

## Resolution

root_cause: JobItem foreign key to Job lacks CASCADE DELETE. When jobs are cleared via bulk delete, JobItems persist as orphans. New jobs reuse old IDs and appear to have accumulated items from previous runs.
fix: |
  1. Added ondelete="CASCADE" to JobItem.job_id foreign key (jobs_model.py)
  2. Modified clear_all_jobs() to explicitly delete JobItems before Jobs (jobs_routes.py)
  3. Modified clear_list_jobs() to explicitly delete JobItems before Jobs (jobs_routes.py)
verification: |
  1. Cleaned 140 orphaned job_items (job_ids 4, 5, 6 with no corresponding jobs)
  2. Cleaned 140 duplicate job_items (old items mixed with new when IDs reused)
  3. Verified all 3 jobs now have correct item counts (20 each)
  4. Code changes verified: ondelete="CASCADE" added, explicit delete in clear endpoints
files_changed:
  - listarr/models/jobs_model.py
  - listarr/routes/jobs_routes.py
