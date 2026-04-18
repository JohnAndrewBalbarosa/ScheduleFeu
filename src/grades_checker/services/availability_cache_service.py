from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from grades_checker.models.entities import AvailabilitySnapshot
from grades_checker.models.entities import CourseOfferingSection
from grades_checker.models.entities import EnrollmentStatus


class AvailabilityCacheService:
    def __init__(self, cache_file: str) -> None:
        self.cache_path = Path(cache_file)

    def exists(self) -> bool:
        return self.cache_path.exists()

    def save_snapshot(self, snapshot: AvailabilitySnapshot) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(asdict(snapshot), indent=2), encoding="utf-8")

    def load_snapshot(self) -> AvailabilitySnapshot:
        raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        enrollment = EnrollmentStatus(**raw["enrollment_status"])
        sections = [CourseOfferingSection(**row) for row in raw["sections"]]
        return AvailabilitySnapshot(
            scraped_at_utc=raw["scraped_at_utc"],
            term_number=raw["term_number"],
            school_year=raw["school_year"],
            used_profile_term=raw["used_profile_term"],
            enrollment_status=enrollment,
            subject_codes=raw["subject_codes"],
            sections=sections,
        )
