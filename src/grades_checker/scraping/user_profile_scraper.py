from __future__ import annotations

import re

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from grades_checker.models.entities import EnrollmentStatus

ENROLLMENT_HEADING_PATTERN = re.compile(r"Term\s*(\d+)\s*SY\s*(\d{8})", re.IGNORECASE)


class UserProfileScraper:
    def __init__(self, page: Page, profile_url: str = "https://solar.feutech.edu.ph/user/profile") -> None:
        self.page = page
        self.profile_url = profile_url

    def _safe_goto_profile(self) -> None:
        last_error: Exception | None = None
        for _ in range(3):
            try:
                self.page.goto(self.profile_url, wait_until="domcontentloaded")
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
        self._safe_goto_profile()

    def wait_for_login(self) -> None:
        if "login.microsoftonline.com" in self.page.url:
            input("Sign in in the opened browser, then press Enter to continue...")
            self.page.wait_for_timeout(1000)
            self.page.wait_for_load_state("domcontentloaded")

        if not self.page.url.startswith(self.profile_url):
            self._safe_goto_profile()

    def scrape_enrollment_status(self) -> EnrollmentStatus:
        heading_locator = self.page.locator("h4", has_text="Enrollment Status").first
        heading_text = heading_locator.inner_text().strip() if heading_locator.count() else ""

        term_number: int | None = None
        school_year: str | None = None

        match = ENROLLMENT_HEADING_PATTERN.search(heading_text)
        if match:
            term_number = int(match.group(1))
            school_year = match.group(2)

        status_table_rows = heading_locator.locator("xpath=following::table[1]//tr") if heading_locator.count() else self.page.locator("table tr")

        values: dict[str, str] = {}
        for idx in range(status_table_rows.count()):
            cells = status_table_rows.nth(idx).locator("td")
            if cells.count() < 2:
                continue
            key = cells.nth(0).inner_text().strip().lower()
            value = cells.nth(1).inner_text().strip()
            if key:
                values[key] = value

        year_level = None
        year_text = values.get("year level", "")
        year_match = re.search(r"(\d+)", year_text)
        if year_match:
            year_level = int(year_match.group(1))

        student_type = values.get("student type", "").strip().upper()
        is_regular = "REGULAR" in student_type

        return EnrollmentStatus(
            term_number=term_number,
            school_year=school_year,
            year_level=year_level,
            student_type=student_type,
            is_regular=is_regular,
            heading_text=heading_text,
        )
