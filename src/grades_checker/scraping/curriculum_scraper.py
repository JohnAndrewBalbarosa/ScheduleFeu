import re
from typing import List

from playwright.sync_api import Page

from grades_checker.config.settings import load_settings
from grades_checker.models.entities import CurriculumCourse

COURSE_CODE_PATTERN = re.compile(r"([A-Z]{2,}\d|NSTP|OJT|THS)")
TERM_BLOCK_PATTERN = re.compile(
    r"(FIRST|SECOND|THIRD|FOURTH|FIFTH)\s+YEAR\s*\(\s*(\d)(?:ST|ND|RD|TH)\s+TERM\s*\)",
    re.IGNORECASE,
)
YEAR_WORD_TO_LEVEL = {
    "FIRST": 1,
    "SECOND": 2,
    "THIRD": 3,
    "FOURTH": 4,
    "FIFTH": 5,
}


class CurriculumScraper:
    def __init__(self, page: Page, curriculum_url: str | None = None) -> None:
        self.page = page
        self.curriculum_url = curriculum_url or load_settings().curriculum_url

    def open(self) -> None:
        self.page.goto(self.curriculum_url, wait_until="domcontentloaded")

    def scrape_courses(self) -> List[CurriculumCourse]:
        rows = self.page.locator("table tbody tr")
        courses: List[CurriculumCourse] = []

        for idx in range(rows.count()):
            cols = rows.nth(idx).locator("td")
            if cols.count() < 3:
                continue

            code = cols.nth(0).inner_text().strip()
            title = cols.nth(1).inner_text().strip()
            units_text = cols.nth(2).inner_text().strip()

            if not COURSE_CODE_PATTERN.search(code):
                continue

            try:
                units = float(units_text)
            except ValueError:
                continue

            courses.append(
                CurriculumCourse(course_code=code, course_title=title, units=units)
            )

        return courses

    def scrape_subject_codes_for_term(self, *, year_level: int, term_number: int) -> list[str]:
        rows = self.page.locator("table tbody tr")
        current_year_level: int | None = None
        current_term_number: int | None = None

        subject_codes: list[str] = []
        seen: set[str] = set()

        for idx in range(rows.count()):
            cols = rows.nth(idx).locator("td")
            if cols.count() < 1:
                continue

            first_cell = cols.nth(0).inner_text().strip()
            header_match = TERM_BLOCK_PATTERN.search(first_cell)
            if header_match:
                year_word = header_match.group(1).upper()
                current_year_level = YEAR_WORD_TO_LEVEL.get(year_word)
                current_term_number = int(header_match.group(2))
                continue

            if current_year_level != year_level or current_term_number != term_number:
                continue

            if cols.count() < 3:
                continue

            code = cols.nth(0).inner_text().strip().upper()
            if not code or not COURSE_CODE_PATTERN.search(code):
                continue

            if code in seen:
                continue
            seen.add(code)
            subject_codes.append(code)

        return subject_codes
