"""
Import Service
Orchestrates importing TMDB list items into Radarr/Sonarr.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """
    Structured result from an import operation.

    Categorizes items into:
    - added: Successfully imported to Radarr/Sonarr
    - skipped: Already existed in library (not an error)
    - failed: Error during import (API error, not found, etc.)
    """
    added: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total items processed."""
        return len(self.added) + len(self.skipped) + len(self.failed)

    @property
    def success_count(self) -> int:
        """Items that succeeded (added + skipped)."""
        return len(self.added) + len(self.skipped)

    @property
    def has_failures(self) -> bool:
        """Whether any items failed to import."""
        return len(self.failed) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'added': self.added,
            'skipped': self.skipped,
            'failed': self.failed,
            'summary': {
                'total': self.total,
                'added_count': len(self.added),
                'skipped_count': len(self.skipped),
                'failed_count': len(self.failed),
            }
        }
