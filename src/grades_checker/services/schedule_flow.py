from __future__ import annotations

from grades_checker.config.settings import load_settings
from grades_checker.logic.schedule import choose_offerings_term_and_year
from grades_checker.logic.schedule import group_sections_for_subjects
from grades_checker.logic.schedule import latest_term_subject_codes
from grades_checker.models.entities import SubjectSections
from grades_checker.scraping.curriculum_scraper import CurriculumScraper
from grades_checker.scraping.course_offerings_scraper import CourseOfferingsScraper
from grades_checker.scraping.session import managed_page
from grades_checker.scraping.user_profile_scraper import UserProfileScraper
from grades_checker.services.availability_cache_service import AvailabilityCacheService
from grades_checker.services.cache_service import CacheService
from grades_checker.services.professor_excel import apply_professor_map
from grades_checker.services.professor_excel import load_professor_map_from_excel
from grades_checker.services.professor_excel import validate_prof_excel_path
from grades_checker.services.schedule_image import render_schedule_png


def _render_grouped_sections(grouped: list[SubjectSections], *, snapshot_time: str, latest_subject_codes: list[str], group_size: int) -> None:
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        console.print(f"[bold]Cached snapshot time:[/bold] {snapshot_time}")
        console.print(f"[bold]Target subjects:[/bold] {', '.join(latest_subject_codes)}")
        console.print(f"[bold]Group size requested:[/bold] {group_size}")
        console.print()

        for item in grouped:
            table = Table(title=f"{item.subject_code} Sections", show_lines=False)
            table.add_column("Section", style="cyan", no_wrap=True)
            table.add_column("Day", style="green", no_wrap=True)
            table.add_column("Time", style="magenta")
            table.add_column("Room", style="yellow")
            table.add_column("Professor", style="white")
            table.add_column("Class Size", justify="right")
            table.add_column("Available", justify="right")

            if not item.sections:
                table.add_row("-", "-", "-", "-", "-", "-", "No matching sections")
                console.print(table)
                console.print()
                continue

            for section in item.sections:
                class_size_text = "unknown" if section.class_size is None else str(section.class_size)
                slots_text = "unknown" if section.available_slots is None else str(section.available_slots)
                table.add_row(
                    section.section_code,
                    section.day or "-",
                    section.time or "-",
                    section.room or "-",
                    section.professor_name or "-",
                    class_size_text,
                    slots_text,
                )

            console.print(table)
            console.print()
        return
    except Exception:
        pass

    print(f"Cached snapshot time: {snapshot_time}")
    print(f"Target subjects: {', '.join(latest_subject_codes)}")
    print(f"Group size requested: {group_size}")
    print()

    for item in grouped:
        print(f"Subject: {item.subject_code}")
        if not item.sections:
            print("- No section found with enough available slots.")
            print()
            continue

        for section in item.sections:
            class_size_text = "unknown" if section.class_size is None else str(section.class_size)
            slots_text = "unknown" if section.available_slots is None else str(section.available_slots)
            print(
                f"- Section {section.section_code} | day: {section.day or '-'} | time: {section.time or '-'} | "
                f"room: {section.room or '-'} | professor: {section.professor_name or '-'} | "
                f"class size: {class_size_text} | available: {slots_text}"
            )
        print()


def run_schedule_from_cache(
    group_size: int,
    image_output: str | None = None,
    prof_excel_path: str | None = None,
) -> None:
    if group_size < 1:
        raise SystemExit("Group size must be at least 1.")

    settings = load_settings()
    cache_service = CacheService(settings.cache_file)
    availability_cache = AvailabilityCacheService(settings.availability_cache_file)
    output_image_path = image_output or ".cache/schedule_report.png"
    validated_prof_excel_path = validate_prof_excel_path(prof_excel_path)

    if not cache_service.exists():
        raise SystemExit("No cached grades snapshot found. Run grades-checker --live first.")

    snapshot = cache_service.load_snapshot()
    fallback_subject_codes = latest_term_subject_codes(snapshot.course_grades, snapshot.term_labels)
    if not fallback_subject_codes:
        raise SystemExit("No latest-term subjects found in cached grade snapshot.")

    if availability_cache.exists():
        availability_snapshot = availability_cache.load_snapshot()
        target_subject_codes = availability_snapshot.subject_codes or fallback_subject_codes
        offerings = availability_snapshot.sections
        source_time = availability_snapshot.scraped_at_utc
    else:
        target_subject_codes = fallback_subject_codes

        with managed_page(headless=False) as page:
            profile_scraper = UserProfileScraper(page)
            profile_scraper.open()
            profile_scraper.wait_for_login()
            enrollment_status = profile_scraper.scrape_enrollment_status()

            term_number, school_year_text, used_profile_term = choose_offerings_term_and_year(
                enrollment_status=enrollment_status,
                term_labels=snapshot.term_labels,
                fallback_course_grades=snapshot.course_grades,
            )

            if enrollment_status.is_regular and enrollment_status.year_level is not None:
                curriculum_scraper = CurriculumScraper(page, settings.curriculum_url)
                curriculum_scraper.open()
                curriculum_subjects = curriculum_scraper.scrape_subject_codes_for_term(
                    year_level=enrollment_status.year_level,
                    term_number=term_number,
                )
                if curriculum_subjects:
                    target_subject_codes = curriculum_subjects

            scraper = CourseOfferingsScraper(page, settings.offerings_url)
            scraper.open()
            scraper.wait_for_login()
            scraper.submit_term_and_school_year(term_number, school_year_text)
            offerings = scraper.scrape_sections()

        from grades_checker.models.entities import AvailabilitySnapshot

        filtered_sections = [row for row in offerings if row.course_code in target_subject_codes]
        cached_at = CacheService.now_utc_iso()
        availability_cache.save_snapshot(
            AvailabilitySnapshot(
                scraped_at_utc=cached_at,
                term_number=term_number,
                school_year=school_year_text,
                used_profile_term=used_profile_term,
                enrollment_status=enrollment_status,
                subject_codes=target_subject_codes,
                sections=filtered_sections,
            )
        )
        offerings = filtered_sections
        source_time = cached_at

    grouped = group_sections_for_subjects(
        subject_codes=target_subject_codes,
        offerings=offerings,
        group_size=group_size,
    )

    if validated_prof_excel_path:
        professor_map = load_professor_map_from_excel(validated_prof_excel_path)
        grouped = apply_professor_map(grouped, professor_map)

    _render_grouped_sections(
        grouped,
        snapshot_time=source_time,
        latest_subject_codes=target_subject_codes,
        group_size=group_size,
    )

    generated_path = render_schedule_png(
        grouped=grouped,
        snapshot_time=source_time,
        target_subject_codes=target_subject_codes,
        group_size=group_size,
        output_path=output_image_path,
    )
    if generated_path:
        print(f"Saved schedule image report: {generated_path}")
    else:
        print("Image report was not generated. Install pillow to enable PNG export.")
