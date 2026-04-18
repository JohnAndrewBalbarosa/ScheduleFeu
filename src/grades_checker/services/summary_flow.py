from grades_checker.config.settings import AppSettings
from grades_checker.config.settings import honor_targets_from_settings
from grades_checker.config.settings import load_settings
from grades_checker.logic.schedule import choose_offerings_term_and_year
from grades_checker.logic.schedule import latest_term_subject_codes
from grades_checker.models.entities import AvailabilitySnapshot
from grades_checker.models.entities import ScrapedSnapshot
from grades_checker.scraping.course_offerings_scraper import CourseOfferingsScraper
from grades_checker.scraping.curriculum_scraper import CurriculumScraper
from grades_checker.scraping.grades_scraper import GradesScraper
from grades_checker.scraping.user_profile_scraper import UserProfileScraper
from grades_checker.scraping.session import managed_page
from grades_checker.services.availability_cache_service import AvailabilityCacheService
from grades_checker.services.cache_service import CacheService
from grades_checker.services.analyzer import GradeAnalyzerService


def scrape_live_snapshot() -> ScrapedSnapshot:
    with managed_page(headless=False) as page:
        grades_scraper = GradesScraper(page)
        curriculum_scraper = CurriculumScraper(page)
        service = GradeAnalyzerService(grades_scraper, curriculum_scraper)
        return service.run_live_snapshot()


def scrape_live_snapshot_and_cache_availability(settings: AppSettings | None = None) -> ScrapedSnapshot:
    app_settings = settings or load_settings()

    with managed_page(headless=False) as page:
        grades_scraper = GradesScraper(page)
        curriculum_scraper = CurriculumScraper(page)
        analyzer = GradeAnalyzerService(grades_scraper, curriculum_scraper)
        snapshot = analyzer.run_live_snapshot()

        profile_scraper = UserProfileScraper(page)
        profile_scraper.open()
        profile_scraper.wait_for_login()
        enrollment_status = profile_scraper.scrape_enrollment_status()

        term_number, school_year, used_profile_term = choose_offerings_term_and_year(
            enrollment_status=enrollment_status,
            term_labels=snapshot.term_labels,
            fallback_course_grades=snapshot.course_grades,
        )

        target_subject_codes = latest_term_subject_codes(snapshot.course_grades, snapshot.term_labels)
        if enrollment_status.is_regular and enrollment_status.year_level is not None:
            curriculum_scraper.open()
            curriculum_subjects = curriculum_scraper.scrape_subject_codes_for_term(
                year_level=enrollment_status.year_level,
                term_number=term_number,
            )
            if curriculum_subjects:
                target_subject_codes = curriculum_subjects

        offerings_scraper = CourseOfferingsScraper(page, app_settings.offerings_url)
        offerings_scraper.open()
        offerings_scraper.wait_for_login()
        offerings_scraper.submit_term_and_school_year(term_number, school_year)
        offerings = offerings_scraper.scrape_sections()

    filtered_sections = [row for row in offerings if row.course_code in target_subject_codes]

    availability_snapshot = AvailabilitySnapshot(
        scraped_at_utc=CacheService.now_utc_iso(),
        term_number=term_number,
        school_year=school_year,
        used_profile_term=used_profile_term,
        enrollment_status=enrollment_status,
        subject_codes=target_subject_codes,
        sections=filtered_sections,
    )
    AvailabilityCacheService(app_settings.availability_cache_file).save_snapshot(availability_snapshot)
    return snapshot


def build_summary(snapshot: ScrapedSnapshot, settings: AppSettings):
    return GradeAnalyzerService.build_summary(
        course_grades=snapshot.course_grades,
        curriculum_courses=snapshot.curriculum_courses,
        term_labels=snapshot.term_labels,
        honor_targets=honor_targets_from_settings(settings),
    )
