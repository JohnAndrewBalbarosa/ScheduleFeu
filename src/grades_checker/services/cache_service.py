from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from grades_checker.models.entities import CourseGrade, CurriculumCourse, ScrapedSnapshot


class CacheService:
    def __init__(self, cache_file: str) -> None:
        self.cache_path = Path(cache_file)

    def exists(self) -> bool:
        return self.cache_path.exists()

    def save_snapshot(self, snapshot: ScrapedSnapshot) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(snapshot)
        self.cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_snapshot(self) -> ScrapedSnapshot:
        raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        grades = [CourseGrade(**row) for row in raw["course_grades"]]
        curriculum = [CurriculumCourse(**row) for row in raw["curriculum_courses"]]
        return ScrapedSnapshot(
            scraped_at_utc=raw["scraped_at_utc"],
            term_labels=raw["term_labels"],
            course_grades=grades,
            curriculum_courses=curriculum,
        )

    @staticmethod
    def now_utc_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
