#!/usr/bin/env python3
"""
Migration script to fix weekly schedule cron expressions.

Background:
APScheduler uses ISO weekday numbering (0=Monday) while standard cron uses (0=Sunday).
Lists created with "0 0 * * 0" were intended for Sunday midnight but execute on Monday.

This script updates affected lists to use "0 0 * * SUN" which all libraries interpret correctly.

Usage:
    python .planning/debug/migrate-schedule-cron.py
"""

import sys

sys.path.insert(0, ".")

# ruff: noqa: E402
from listarr import create_app, db
from listarr.models.lists_model import List


def migrate_schedules():
    """Update weekly schedule cron expressions from numeric to text format."""
    app = create_app()

    with app.app_context():
        # Find lists with the problematic cron expression
        affected_lists = List.query.filter_by(schedule_cron="0 0 * * 0").all()

        if not affected_lists:
            print("No lists found with schedule '0 0 * * 0'")
            print("Migration not needed.")
            return

        print(f"Found {len(affected_lists)} list(s) to migrate:")
        for lst in affected_lists:
            print(f"  - List ID {lst.id}: {lst.name}")

        # Confirm migration
        response = input("\nUpdate these lists to use '0 0 * * SUN'? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Migration cancelled.")
            return

        # Perform migration
        for lst in affected_lists:
            old_cron = lst.schedule_cron
            lst.schedule_cron = "0 0 * * SUN"
            print(f"  Updated List ID {lst.id}: '{old_cron}' -> '{lst.schedule_cron}'")

        db.session.commit()
        print(f"\nMigration complete. {len(affected_lists)} list(s) updated.")
        print("\nNOTE: Restart the application to reload the scheduler with the new cron expressions.")


if __name__ == "__main__":
    migrate_schedules()
