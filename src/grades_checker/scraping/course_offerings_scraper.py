from __future__ import annotations

import re
from typing import List

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from grades_checker.config.settings import load_settings
from grades_checker.models.entities import CourseOfferingSection

COURSE_CODE_PATTERN = re.compile(r"\b([A-Z]{2,}\d{2,}[A-Z]?|NSTP\d?|OJT|THS\d?)\b")
SLOTS_LEFT_PATTERN = re.compile(r"(\d+)\s+slots?\s+left", re.IGNORECASE)
AVAILABLE_PATTERN = re.compile(r"available\s*[:\-]?\s*(\d+)", re.IGNORECASE)
ENROLLED_CAPACITY_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)")


class CourseOfferingsScraper:
    def __init__(self, page: Page, offerings_url: str | None = None) -> None:
        self.page = page
        self.offerings_url = offerings_url or load_settings().offerings_url

    def _safe_goto_offerings(self) -> None:
        last_error: Exception | None = None
        for _ in range(3):
            try:
                self.page.goto(self.offerings_url, wait_until="domcontentloaded")
                self.page.wait_for_load_state("networkidle")
                return
            except PlaywrightError as exc:
                last_error = exc
                if "interrupted by another navigation" in str(exc):
                    self.page.wait_for_timeout(800)
                    continue
                raise

        if last_error is not None:
            raise last_error

    def open(self) -> None:
        self._safe_goto_offerings()

    def wait_for_login(self) -> None:
        if "login.microsoftonline.com" in self.page.url:
            input("Sign in in the opened browser, then press Enter to continue...")
            self.page.wait_for_timeout(1000)
            self.page.wait_for_load_state("domcontentloaded")

        if not self.page.url.startswith(self.offerings_url):
            self._safe_goto_offerings()

    def _extract_course_code(self, row_text: str) -> str | None:
        match = COURSE_CODE_PATTERN.search(row_text.upper())
        if not match:
            return None
        return match.group(1).strip().upper()

    def _extract_section_code(self, columns: list[str], course_code: str) -> str:
        for text in columns:
            candidate = text.strip()
            if not candidate:
                continue
            if candidate.upper() == course_code:
                continue
            if len(candidate) > 60:
                continue
            if COURSE_CODE_PATTERN.search(candidate.upper()):
                continue
            return candidate
        return "(unknown section)"

    @staticmethod
    def _to_int_or_none(text: str) -> int | None:
        digits = re.sub(r"[^0-9]", "", text)
        if not digits:
            return None
        return int(digits)

    def _extract_available_slots(self, row_text: str) -> int | None:
        lowered = row_text.lower()
        if "full" in lowered:
            return 0

        match = SLOTS_LEFT_PATTERN.search(row_text)
        if match:
            return int(match.group(1))

        match = AVAILABLE_PATTERN.search(row_text)
        if match:
            return int(match.group(1))

        match = ENROLLED_CAPACITY_PATTERN.search(row_text)
        if match:
            enrolled = int(match.group(1))
            capacity = int(match.group(2))
            if enrolled <= capacity:
                return max(0, capacity - enrolled)

        return None

    def submit_term_and_school_year(self, term_number: int, school_year: str) -> None:
        term_value = str(term_number)
        self.page.locator("#term").select_option(value=term_value)
        self.page.locator("#school_year").select_option(value=school_year)
        self.page.get_by_role("button", name="Submit").click()
        self.page.wait_for_load_state("networkidle")

    def scrape_sections(self) -> List[CourseOfferingSection]:
        rows = self.page.locator("#courseOfferingsTable tbody tr")
        sections: List[CourseOfferingSection] = []

        for idx in range(rows.count()):
            cols = rows.nth(idx).locator("td")
            if cols.count() < 2:
                continue

            columns = [cols.nth(col_idx).inner_text().strip() for col_idx in range(cols.count())]
            row_text = " | ".join(columns)

            # Verified structure: COURSE, SECTION, CLASS SIZE, REMAINING, DAY, TIME, ROOM
            course_code = columns[0].strip().upper() if len(columns) >= 1 else ""
            section_code = columns[1].strip() if len(columns) >= 2 else ""
            class_size_text = columns[2].strip() if len(columns) >= 3 else ""
            remaining_text = columns[3].strip() if len(columns) >= 4 else ""
            day_text = columns[4].strip() if len(columns) >= 5 else ""
            time_text = columns[5].strip() if len(columns) >= 6 else ""
            room_text = columns[6].strip() if len(columns) >= 7 else ""

            if not course_code:
                course_code = self._extract_course_code(row_text) or ""
            if not section_code:
                section_code = self._extract_section_code(columns, course_code)

            if not course_code:
                continue

            available_slots = self._to_int_or_none(remaining_text)
            if available_slots is None:
                available_slots = self._extract_available_slots(row_text)
            class_size = self._to_int_or_none(class_size_text)

            sections.append(
                CourseOfferingSection(
                    course_code=course_code,
                    section_code=section_code,
                    available_slots=available_slots,
                    details=row_text,
                    class_size=class_size,
                    day=day_text,
                    time=time_text,
                    room=room_text,
                )
            )

        return sections
