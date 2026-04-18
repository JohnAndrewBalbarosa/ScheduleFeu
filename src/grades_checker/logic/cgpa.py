from typing import Iterable

from grades_checker.models.entities import CourseGrade


MAX_GRADE = 4.0


def compute_weighted_totals(course_grades: Iterable[CourseGrade]) -> tuple[float, float]:
    total_units = 0.0
    total_quality_points = 0.0
    for row in course_grades:
        if row.units <= 0:
            continue
        total_units += row.units
        total_quality_points += row.units * row.final_grade
    return total_units, total_quality_points


def compute_cgpa(course_grades: Iterable[CourseGrade]) -> tuple[float, float]:
    total_units, total_quality_points = compute_weighted_totals(course_grades)
    if total_units == 0:
        return 0.0, 0.0
    return total_quality_points / total_units, total_units


def required_average_for_target(
    *,
    current_cgpa: float,
    completed_units: float,
    total_curriculum_units: float,
    target_cgpa: float,
) -> float:
    remaining_units = total_curriculum_units - completed_units
    if remaining_units <= 0:
        return 0.0 if current_cgpa >= target_cgpa else float("inf")

    current_quality_points = current_cgpa * completed_units
    required_quality_points = (target_cgpa * total_curriculum_units) - current_quality_points
    return required_quality_points / remaining_units
