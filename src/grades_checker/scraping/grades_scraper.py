from typing import List

from playwright.sync_api import Page
from playwright.sync_api import Error as PlaywrightError

from grades_checker.config.settings import load_settings
from grades_checker.logic.terms import sort_term_labels
from grades_checker.models.entities import CourseGrade, TermOption

class GradesScraper:
    def __init__(self, page: Page, grades_url: str | None = None) -> None:
        self.page = page
        self.grades_url = grades_url or load_settings().grades_url

    def _safe_goto_grades(self) -> None:
        """Navigate to grades page while tolerating transient redirect races."""
        last_error: Exception | None = None
        for _ in range(3):
            try:
                self.page.goto(self.grades_url, wait_until="domcontentloaded")
                self.page.wait_for_load_state("networkidle")
                return
            except PlaywrightError as exc:
                # Login callbacks can trigger overlapping redirects; retry shortly after.
                last_error = exc
                if "interrupted by another navigation" in str(exc):
                    self.page.wait_for_timeout(800)
                    continue
                raise

        if last_error is not None:
            raise last_error

    def open(self) -> None:
        self._safe_goto_grades()

    def wait_for_login(self) -> None:
        if "login.microsoftonline.com" in self.page.url:
            input("Sign in in the opened browser, then press Enter to continue...")

            # Allow post-login redirects to settle before forcing another navigation.
            self.page.wait_for_timeout(1000)
            self.page.wait_for_load_state("domcontentloaded")

        if not self.page.url.startswith(self.grades_url):
            self._safe_goto_grades()

    def list_term_options(self) -> List[TermOption]:
        options = self.page.locator("select option")
        terms: List[TermOption] = []
        for i in range(options.count()):
            label = options.nth(i).inner_text().strip()
            value = options.nth(i).get_attribute("value") or label
            if not label or label == "--":
                continue
            terms.append(TermOption(label=label, value=value))
        sorted_labels = sort_term_labels([term.label for term in terms])
        by_label = {term.label: term for term in terms}
        return [by_label[label] for label in sorted_labels]

    def scrape_term(self, term_label: str) -> List[CourseGrade]:
        self.page.locator("select").first.select_option(label=term_label)
        self.page.get_by_role("button", name="Submit").click()
        self.page.wait_for_load_state("domcontentloaded")

        rows = self.page.locator("table tbody tr")
        course_grades: List[CourseGrade] = []
        for idx in range(rows.count()):
            cols = rows.nth(idx).locator("td")
            if cols.count() < 6:
                continue

            course_code = cols.nth(0).inner_text().strip()
            course_title = cols.nth(1).inner_text().strip()
            units_text = cols.nth(3).inner_text().strip()
            final_text = cols.nth(5).inner_text().strip()

            try:
                units = float(units_text)
                final_grade = float(final_text)
            except ValueError:
                continue

            course_grades.append(
                CourseGrade(
                    term_label=term_label,
                    course_code=course_code,
                    course_title=course_title,
                    units=units,
                    final_grade=final_grade,
                )
            )

        return course_grades

    def scrape_all_terms(self) -> tuple[List[CourseGrade], List[str]]:
        all_rows: List[CourseGrade] = []
        term_labels: List[str] = []
        for term in self.list_term_options():
            term_labels.append(term.label)
            all_rows.extend(self.scrape_term(term.label))
        return all_rows, term_labels
