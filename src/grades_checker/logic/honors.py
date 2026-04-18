from grades_checker.logic.cgpa import MAX_GRADE, required_average_for_target
from grades_checker.models.entities import HonorResult


HONOR_TARGETS: tuple[tuple[str, float], ...] = (
    ("Summa Cum Laude", 3.80),
    ("Magna Cum Laude", 3.60),
    ("Cum Laude", 3.40),
)


def evaluate_honors(
    *,
    current_cgpa: float,
    completed_units: float,
    total_curriculum_units: float,
    honor_targets: tuple[tuple[str, float], ...] = HONOR_TARGETS,
) -> list[HonorResult]:
    results: list[HonorResult] = []

    for honor_name, target in honor_targets:
        needed = required_average_for_target(
            current_cgpa=current_cgpa,
            completed_units=completed_units,
            total_curriculum_units=total_curriculum_units,
            target_cgpa=target,
        )
        qualified_now = current_cgpa >= target
        reachable = needed <= MAX_GRADE
        results.append(
            HonorResult(
                honor_name=honor_name,
                target_gpa=target,
                qualified_now=qualified_now,
                needed_average_for_remaining_units=needed,
                reachable=reachable,
            )
        )

    return results
