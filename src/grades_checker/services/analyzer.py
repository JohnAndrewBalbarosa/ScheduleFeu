from grades_checker.logic.cgpa import compute_cgpa
from grades_checker.logic.honors import HONOR_TARGETS
from grades_checker.logic.honors import evaluate_honors
from grades_checker.models.entities import AnalysisSummary, CourseGrade, CurriculumCourse, ScrapedSnapshot
from grades_checker.scraping.curriculum_scraper import CurriculumScraper
from grades_checker.scraping.grades_scraper import GradesScraper


class GradeAnalyzerService:
    def __init__(self, grades_scraper: GradesScraper, curriculum_scraper: CurriculumScraper) -> None:
        self.grades_scraper = grades_scraper
        self.curriculum_scraper = curriculum_scraper

    def run_live_analysis(self) -> AnalysisSummary:
        self.grades_scraper.open()
        self.grades_scraper.wait_for_login()
        course_grades, term_labels = self.grades_scraper.scrape_all_terms()

        self.curriculum_scraper.open()
        curriculum_courses = self.curriculum_scraper.scrape_courses()

        return self.build_summary(
            course_grades=course_grades,
            curriculum_courses=curriculum_courses,
            term_labels=term_labels,
        )

    def run_live_snapshot(self) -> ScrapedSnapshot:
        self.grades_scraper.open()
        self.grades_scraper.wait_for_login()
        course_grades, term_labels = self.grades_scraper.scrape_all_terms()

        self.curriculum_scraper.open()
        curriculum_courses = self.curriculum_scraper.scrape_courses()

        from grades_checker.services.cache_service import CacheService

        return ScrapedSnapshot(
            scraped_at_utc=CacheService.now_utc_iso(),
            term_labels=term_labels,
            course_grades=course_grades,
            curriculum_courses=curriculum_courses,
        )

    @staticmethod
    def build_summary(
        *,
        course_grades: list[CourseGrade],
        curriculum_courses: list[CurriculumCourse],
        term_labels: list[str],
        honor_targets: tuple[tuple[str, float], ...] | None = None,
    ) -> AnalysisSummary:
        current_cgpa, completed_units = compute_cgpa(course_grades)
        total_curriculum_units = sum(course.units for course in curriculum_courses)
        remaining_units = max(0.0, total_curriculum_units - completed_units)

        honors = evaluate_honors(
            current_cgpa=current_cgpa,
            completed_units=completed_units,
            total_curriculum_units=total_curriculum_units,
            honor_targets=honor_targets if honor_targets is not None else HONOR_TARGETS,
        )

        return AnalysisSummary(
            current_cgpa=current_cgpa,
            completed_units=completed_units,
            total_curriculum_units=total_curriculum_units,
            remaining_units=remaining_units,
            term_labels=term_labels,
            first_term_label=term_labels[0] if term_labels else "N/A",
            latest_term_label=term_labels[-1] if term_labels else "N/A",
            honors=honors,
        )
