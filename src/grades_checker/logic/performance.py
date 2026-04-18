from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable

from grades_checker.logic.cgpa import compute_cgpa
from grades_checker.logic.honors import evaluate_honors
from grades_checker.models.entities import CourseGrade, HonorResult


@dataclass(frozen=True)
class OutlierSubject:
    course_code: str
    course_title: str
    term_label: str
    final_grade: float
    robust_z: float


@dataclass(frozen=True)
class OutlierAnalysisResult:
    term_label: str
    baseline_grade: float
    baseline_grade_rounded: float
    low_outliers: list[OutlierSubject]
    compared_subject_count: int
    reference_subject_count: int
    cgpa_gain: float
    projected_cgpa_without_low_outliers: float
    projected_honors: list[HonorResult]


@dataclass(frozen=True)
class FailedRecoveryResult:
    failed_subjects: list[CourseGrade]
    replacement_grade: float
    projected_cgpa_without_failed_subjects: float
    cgpa_gain: float
    projected_honors: list[HonorResult]


def build_term_grade_index(course_grades: Iterable[CourseGrade]) -> dict[str, list[CourseGrade]]:
    """Build a dictionary index of scraped rows by term label."""
    buckets: dict[str, list[CourseGrade]] = {}
    for row in course_grades:
        if row.units <= 0:
            continue
        buckets.setdefault(row.term_label, []).append(row)
    return buckets


def round_to_half_step(value: float) -> float:
    rounded = round(value * 2) / 2
    if rounded < 0.0:
        return 0.0
    if rounded > 4.0:
        return 4.0
    return rounded


def is_failed_grade(grade: float, failed_grade_values: tuple[float, ...], epsilon: float = 1e-6) -> bool:
    # In this grading system, values above 4.0 are special markers and not failures.
    if grade > 4.0:
        return False
    return any(abs(grade - marker) <= epsilon for marker in failed_grade_values)


def get_failed_subjects(
    course_grades: Iterable[CourseGrade],
    failed_grade_values: tuple[float, ...],
) -> list[CourseGrade]:
    return [
        row
        for row in course_grades
        if row.units > 0 and is_failed_grade(row.final_grade, failed_grade_values)
    ]


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * q
    low = int(pos)
    high = min(low + 1, len(values) - 1)
    frac = pos - low
    return values[low] * (1 - frac) + values[high] * frac


def _trimmed_mean(values: list[float], trim_ratio: float = 0.1) -> float:
    if not values:
        return 0.0
    if len(values) < 5:
        return sum(values) / len(values)
    n = len(values)
    trim_n = int(n * trim_ratio)
    kept = values[trim_n : n - trim_n] if trim_n * 2 < n else values
    return sum(kept) / len(kept)


def _baseline_from_reference(reference: list[float], estimator: str) -> float:
    ordered = sorted(reference)
    if not ordered:
        return 0.0
    if estimator == "median":
        return median(ordered)
    return _trimmed_mean(ordered)


def _mad_scores(values: list[float]) -> tuple[float, float]:
    med = median(values)
    deviations = [abs(x - med) for x in values]
    mad = median(deviations)
    return med, mad


def _is_iqr_low_outlier(value: float, ordered: list[float]) -> bool:
    q1 = _quantile(ordered, 0.25)
    q3 = _quantile(ordered, 0.75)
    iqr = q3 - q1
    if iqr == 0:
        return False
    lower_bound = q1 - (1.5 * iqr)
    return value < lower_bound


def analyze_outliers_for_term(
    *,
    course_grades: Iterable[CourseGrade],
    term_label: str,
    completed_units: float,
    total_curriculum_units: float,
    honor_targets: tuple[tuple[str, float], ...],
    outlier_method: str,
    outlier_tail: str,
    z_threshold: float,
    baseline_estimator: str,
) -> OutlierAnalysisResult:
    term_index = build_term_grade_index(course_grades)
    target_rows = term_index.get(term_label, [])
    reference_rows = [
        row
        for label, rows in term_index.items()
        if label != term_label
        for row in rows
    ]
    rows = [row for rows in term_index.values() for row in rows]
    reference_grades = [row.final_grade for row in reference_rows]

    if not target_rows or not reference_grades:
        actual_cgpa, _ = compute_cgpa(rows)
        projected_honors = evaluate_honors(
            current_cgpa=actual_cgpa,
            completed_units=completed_units,
            total_curriculum_units=total_curriculum_units,
            honor_targets=honor_targets,
        )
        return OutlierAnalysisResult(
            term_label=term_label,
            baseline_grade=0.0,
            baseline_grade_rounded=0.0,
            low_outliers=[],
            compared_subject_count=len(target_rows),
            reference_subject_count=len(reference_rows),
            cgpa_gain=0.0,
            projected_cgpa_without_low_outliers=actual_cgpa,
            projected_honors=projected_honors,
        )

    baseline_grade = _baseline_from_reference(reference_grades, baseline_estimator)
    baseline_grade_rounded = round_to_half_step(baseline_grade)

    med, mad = _mad_scores(reference_grades)
    ordered_reference = sorted(reference_grades)

    low_outliers: list[OutlierSubject] = []
    use_left_tail = outlier_tail == "left"
    for row in target_rows:
        if outlier_method == "iqr":
            robust_z = 0.0
            is_low_outlier = use_left_tail and _is_iqr_low_outlier(row.final_grade, ordered_reference)
        elif mad > 0:
            robust_z = 0.6745 * ((row.final_grade - med) / mad)
            is_low_outlier = use_left_tail and robust_z <= (-1 * z_threshold)
        else:
            robust_z = 0.0
            is_low_outlier = use_left_tail and _is_iqr_low_outlier(row.final_grade, ordered_reference)

        if is_low_outlier:
            low_outliers.append(
                OutlierSubject(
                    course_code=row.course_code,
                    course_title=row.course_title,
                    term_label=row.term_label,
                    final_grade=row.final_grade,
                    robust_z=robust_z,
                )
            )

    adjusted_rows: list[CourseGrade] = []
    low_outlier_codes = {item.course_code for item in low_outliers}
    for row in rows:
        if row.term_label == term_label and row.course_code in low_outlier_codes:
            adjusted_rows.append(
                CourseGrade(
                    term_label=row.term_label,
                    course_code=row.course_code,
                    course_title=row.course_title,
                    units=row.units,
                    final_grade=baseline_grade_rounded,
                )
            )
        else:
            adjusted_rows.append(row)

    actual_cgpa, _ = compute_cgpa(rows)
    projected_cgpa, _ = compute_cgpa(adjusted_rows)
    projected_honors = evaluate_honors(
        current_cgpa=projected_cgpa,
        completed_units=completed_units,
        total_curriculum_units=total_curriculum_units,
        honor_targets=honor_targets,
    )

    return OutlierAnalysisResult(
        term_label=term_label,
        baseline_grade=baseline_grade,
        baseline_grade_rounded=baseline_grade_rounded,
        low_outliers=low_outliers,
        compared_subject_count=len(target_rows),
        reference_subject_count=len(reference_rows),
        cgpa_gain=projected_cgpa - actual_cgpa,
        projected_cgpa_without_low_outliers=projected_cgpa,
        projected_honors=projected_honors,
    )


def analyze_outliers_all_data(
    *,
    course_grades: Iterable[CourseGrade],
    completed_units: float,
    total_curriculum_units: float,
    honor_targets: tuple[tuple[str, float], ...],
    outlier_method: str,
    outlier_tail: str,
    z_threshold: float,
    baseline_estimator: str,
) -> OutlierAnalysisResult:
    rows = [row for row in course_grades if row.units > 0]
    grades = [row.final_grade for row in rows]

    actual_cgpa, _ = compute_cgpa(rows)
    if not rows or not grades:
        projected_honors = evaluate_honors(
            current_cgpa=actual_cgpa,
            completed_units=completed_units,
            total_curriculum_units=total_curriculum_units,
            honor_targets=honor_targets,
        )
        return OutlierAnalysisResult(
            term_label="ALL_TERMS",
            baseline_grade=0.0,
            baseline_grade_rounded=0.0,
            low_outliers=[],
            compared_subject_count=len(rows),
            reference_subject_count=len(rows),
            cgpa_gain=0.0,
            projected_cgpa_without_low_outliers=actual_cgpa,
            projected_honors=projected_honors,
        )

    med, mad = _mad_scores(grades)
    ordered = sorted(grades)
    use_left_tail = outlier_tail == "left"

    low_outliers: list[OutlierSubject] = []
    for row in rows:
        if outlier_method == "iqr":
            robust_z = 0.0
            is_low_outlier = use_left_tail and _is_iqr_low_outlier(row.final_grade, ordered)
        elif mad > 0:
            robust_z = 0.6745 * ((row.final_grade - med) / mad)
            is_low_outlier = use_left_tail and robust_z <= (-1 * z_threshold)
        else:
            robust_z = 0.0
            is_low_outlier = use_left_tail and _is_iqr_low_outlier(row.final_grade, ordered)

        if is_low_outlier:
            low_outliers.append(
                OutlierSubject(
                    course_code=row.course_code,
                    course_title=row.course_title,
                    term_label=row.term_label,
                    final_grade=row.final_grade,
                    robust_z=robust_z,
                )
            )

    non_outlier_grades = [
        row.final_grade
        for row in rows
        if not any(
            row.term_label == out.term_label
            and row.course_code == out.course_code
            and row.course_title == out.course_title
            and row.final_grade == out.final_grade
            for out in low_outliers
        )
    ]
    baseline_reference = non_outlier_grades if non_outlier_grades else grades
    baseline_grade = _baseline_from_reference(baseline_reference, baseline_estimator)
    baseline_grade_rounded = round_to_half_step(baseline_grade)

    outlier_keys = {
        (item.term_label, item.course_code, item.course_title, item.final_grade)
        for item in low_outliers
    }
    adjusted_rows: list[CourseGrade] = []
    for row in rows:
        key = (row.term_label, row.course_code, row.course_title, row.final_grade)
        if key in outlier_keys:
            adjusted_rows.append(
                CourseGrade(
                    term_label=row.term_label,
                    course_code=row.course_code,
                    course_title=row.course_title,
                    units=row.units,
                    final_grade=baseline_grade_rounded,
                )
            )
        else:
            adjusted_rows.append(row)

    projected_cgpa, _ = compute_cgpa(adjusted_rows)
    projected_honors = evaluate_honors(
        current_cgpa=projected_cgpa,
        completed_units=completed_units,
        total_curriculum_units=total_curriculum_units,
        honor_targets=honor_targets,
    )

    return OutlierAnalysisResult(
        term_label="ALL_TERMS",
        baseline_grade=baseline_grade,
        baseline_grade_rounded=baseline_grade_rounded,
        low_outliers=low_outliers,
        compared_subject_count=len(rows),
        reference_subject_count=len(rows),
        cgpa_gain=projected_cgpa - actual_cgpa,
        projected_cgpa_without_low_outliers=projected_cgpa,
        projected_honors=projected_honors,
    )


def analyze_failed_subject_recovery(
    *,
    course_grades: Iterable[CourseGrade],
    completed_units: float,
    total_curriculum_units: float,
    honor_targets: tuple[tuple[str, float], ...],
    failed_grade_values: tuple[float, ...],
    baseline_estimator: str,
) -> FailedRecoveryResult:
    rows = [row for row in course_grades if row.units > 0]
    actual_cgpa, _ = compute_cgpa(rows)

    failed_subjects = get_failed_subjects(rows, failed_grade_values)
    if not failed_subjects:
        projected_honors = evaluate_honors(
            current_cgpa=actual_cgpa,
            completed_units=completed_units,
            total_curriculum_units=total_curriculum_units,
            honor_targets=honor_targets,
        )
        return FailedRecoveryResult(
            failed_subjects=[],
            replacement_grade=0.0,
            projected_cgpa_without_failed_subjects=actual_cgpa,
            cgpa_gain=0.0,
            projected_honors=projected_honors,
        )

    non_failed_grades = [
        row.final_grade for row in rows if not is_failed_grade(row.final_grade, failed_grade_values)
    ]
    baseline_source = non_failed_grades if non_failed_grades else [row.final_grade for row in rows]
    replacement_grade = round_to_half_step(_baseline_from_reference(baseline_source, baseline_estimator))

    failed_keys = {
        (row.term_label, row.course_code, row.course_title, row.final_grade)
        for row in failed_subjects
    }
    adjusted_rows: list[CourseGrade] = []
    for row in rows:
        key = (row.term_label, row.course_code, row.course_title, row.final_grade)
        if key in failed_keys:
            adjusted_rows.append(
                CourseGrade(
                    term_label=row.term_label,
                    course_code=row.course_code,
                    course_title=row.course_title,
                    units=row.units,
                    final_grade=replacement_grade,
                )
            )
        else:
            adjusted_rows.append(row)

    projected_cgpa, _ = compute_cgpa(adjusted_rows)
    projected_honors = evaluate_honors(
        current_cgpa=projected_cgpa,
        completed_units=completed_units,
        total_curriculum_units=total_curriculum_units,
        honor_targets=honor_targets,
    )

    return FailedRecoveryResult(
        failed_subjects=failed_subjects,
        replacement_grade=replacement_grade,
        projected_cgpa_without_failed_subjects=projected_cgpa,
        cgpa_gain=projected_cgpa - actual_cgpa,
        projected_honors=projected_honors,
    )


def auto_select_outlier_term(
    *,
    course_grades: Iterable[CourseGrade],
    term_labels: list[str],
    completed_units: float,
    total_curriculum_units: float,
    honor_targets: tuple[tuple[str, float], ...],
    outlier_method: str,
    outlier_tail: str,
    z_threshold: float,
    baseline_estimator: str,
) -> tuple[OutlierAnalysisResult | None, list[OutlierAnalysisResult]]:
    all_results: list[OutlierAnalysisResult] = []
    for label in term_labels:
        all_results.append(
            analyze_outliers_for_term(
                course_grades=course_grades,
                term_label=label,
                completed_units=completed_units,
                total_curriculum_units=total_curriculum_units,
                honor_targets=honor_targets,
                outlier_method=outlier_method,
                outlier_tail=outlier_tail,
                z_threshold=z_threshold,
                baseline_estimator=baseline_estimator,
            )
        )

    candidates = [result for result in all_results if result.low_outliers]
    if not candidates:
        return None, all_results

    chosen = max(candidates, key=lambda item: (len(item.low_outliers), item.cgpa_gain))
    return chosen, all_results
