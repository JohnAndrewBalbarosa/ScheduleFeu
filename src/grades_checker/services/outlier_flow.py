from grades_checker.config.settings import AppSettings
from grades_checker.config.settings import honor_targets_from_settings
from grades_checker.logic.performance import analyze_failed_subject_recovery
from grades_checker.logic.performance import analyze_outliers_all_data
from grades_checker.models.entities import ScrapedSnapshot
from grades_checker.services.outlier_output import print_failed_recovery
from grades_checker.services.outlier_output import print_failed_subjects
from grades_checker.services.outlier_output import print_low_outliers
from grades_checker.services.outlier_output import print_outlier_header
from grades_checker.services.outlier_output import print_projected_honors
from grades_checker.services.summary_flow import build_summary


def run_outlier_report(snapshot: ScrapedSnapshot, settings: AppSettings) -> None:
    summary = build_summary(snapshot, settings)

    failed_recovery = analyze_failed_subject_recovery(
        course_grades=snapshot.course_grades,
        completed_units=summary.completed_units,
        total_curriculum_units=summary.total_curriculum_units,
        honor_targets=honor_targets_from_settings(settings),
        failed_grade_values=settings.failed_grade_values,
        baseline_estimator=settings.baseline_estimator,
    )
    result = analyze_outliers_all_data(
        course_grades=snapshot.course_grades,
        completed_units=summary.completed_units,
        total_curriculum_units=summary.total_curriculum_units,
        honor_targets=honor_targets_from_settings(settings),
        outlier_method=settings.outlier_method,
        outlier_tail=settings.outlier_tail,
        z_threshold=settings.outlier_z_threshold,
        baseline_estimator=settings.baseline_estimator,
    )

    print_outlier_header(result)
    print_failed_subjects(failed_recovery.failed_subjects)
    print_low_outliers(summary, result)
    print(f"Estimated CGPA gain under average-performance replacement: {result.cgpa_gain:+.3f}")
    print(f"Projected CGPA without low outliers: {result.projected_cgpa_without_low_outliers:.3f}")
    print_failed_recovery(failed_recovery)
    print_projected_honors(result)
