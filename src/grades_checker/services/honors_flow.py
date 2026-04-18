from grades_checker.config.settings import AppSettings
from grades_checker.config.settings import honor_targets_from_settings
from grades_checker.config.settings import load_settings
from grades_checker.logic.honors import evaluate_honors
from grades_checker.logic.performance import get_failed_subjects
from grades_checker.models.entities import HonorResult
from grades_checker.models.entities import ScrapedSnapshot
from grades_checker.services.summary_flow import build_summary
from grades_checker.services.summary_flow import scrape_live_snapshot_and_cache_availability
from grades_checker.services.summary_flow import scrape_live_snapshot


def print_honor_sentences(
    *,
    current_cgpa: float,
    remaining_units: float,
    total_units: float,
    completed_units: float,
    honors: list[HonorResult],
    disqualified_for_failed_subjects: bool = False,
) -> None:
    print(f"CGPA: {current_cgpa:.3f}")
    print(f"Completed units: {completed_units:.0f}")
    print(f"Total curriculum units: {total_units:.0f}")
    print(f"Remaining units: {remaining_units:.0f}")
    print()
    if disqualified_for_failed_subjects:
        print("You are automatically disqualified for Latin honors because at least one subject is failed.")
        for row in honors:
            print(f"- {row.honor_name}: disqualified due to failed subjects.")
        return

    for row in honors:
        if row.qualified_now:
            print(f"You are already qualified for {row.honor_name}.")
        elif not row.reachable:
            print(
                f"You are not qualified for {row.honor_name}, and it is no longer reachable because "
                f"you would need a {row.needed_average_for_remaining_units:.3f} average in your remaining units."
            )
        else:
            print(
                f"You are not yet qualified for {row.honor_name}; to reach it, you need at least "
                f"a {row.needed_average_for_remaining_units:.3f} average in your remaining units."
            )


def run_honors_from_snapshot(snapshot: ScrapedSnapshot, settings: AppSettings) -> None:
    summary = build_summary(snapshot, settings)

    print(
        f"Scraped terms in order: {summary.first_term_label} up to {summary.latest_term_label} "
        f"({len(summary.term_labels)} terms)."
    )
    print(f"Computed CGPA from scraped grades: {summary.current_cgpa:.3f}")

    selected_cgpa = summary.current_cgpa
    honors = evaluate_honors(
        current_cgpa=selected_cgpa,
        completed_units=summary.completed_units,
        total_curriculum_units=summary.total_curriculum_units,
        honor_targets=honor_targets_from_settings(settings),
    )

    failed_subjects = get_failed_subjects(snapshot.course_grades, settings.failed_grade_values)
    if failed_subjects:
        print("Failed subjects detected:")
        for row in failed_subjects:
            print(f"- {row.term_label}: {row.course_code} {row.course_title} ({row.final_grade:.1f})")
        print()

    print_honor_sentences(
        current_cgpa=selected_cgpa,
        remaining_units=summary.remaining_units,
        total_units=summary.total_curriculum_units,
        completed_units=summary.completed_units,
        honors=honors,
        disqualified_for_failed_subjects=bool(failed_subjects),
    )


def run_live() -> None:
    settings = load_settings()
    snapshot = scrape_live_snapshot_and_cache_availability(settings)
    run_honors_from_snapshot(snapshot, settings)


def run_simulation(cgpa: float, completed_units: float, total_units: float) -> None:
    remaining_units = max(0.0, total_units - completed_units)
    settings = load_settings()
    honors = evaluate_honors(
        current_cgpa=cgpa,
        completed_units=completed_units,
        total_curriculum_units=total_units,
        honor_targets=honor_targets_from_settings(settings),
    )
    print_honor_sentences(
        current_cgpa=cgpa,
        remaining_units=remaining_units,
        total_units=total_units,
        completed_units=completed_units,
        honors=honors,
    )
