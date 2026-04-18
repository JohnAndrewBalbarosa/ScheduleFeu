from collections import defaultdict


def print_outlier_header(result) -> None:
    print()
    print("Outlier analysis using all scraped subjects across all terms")
    print(
        f"Compared subjects: {result.compared_subject_count}; "
        f"reference subjects: {result.reference_subject_count}"
    )
    print(
        "Expected baseline grade from non-outlier terms: "
        f"{result.baseline_grade:.3f} (rounded to {result.baseline_grade_rounded:.1f} for 0.5-step grading)"
    )


def print_failed_subjects(failed_subjects: list) -> None:
    if failed_subjects:
        print("Failed subjects detected (auto-disqualifier for Latin honors):")
        for row in failed_subjects:
            print(f"- {row.term_label}: {row.course_code} {row.course_title} ({row.final_grade:.1f})")
    else:
        print("No failed subjects detected in scraped records.")


def print_low_outliers(summary, result) -> None:
    if not result.low_outliers:
        print("No low outlier subjects detected across all terms.")
        return

    print("Low outlier subjects found (all terms):")
    grouped: dict[str, list] = defaultdict(list)
    for item in result.low_outliers:
        grouped[item.term_label].append(item)

    for term in summary.term_labels:
        items = grouped.get(term, [])
        if not items:
            continue
        print(f"- {term}")
        for item in items:
            delta = result.baseline_grade_rounded - item.final_grade
            print(
                f"  {item.course_code} {item.course_title}: {item.final_grade:.3f} "
                f"(robust z={item.robust_z:.3f})"
            )
            print(
                f"    simulated replacement: {item.final_grade:.1f} -> "
                f"{result.baseline_grade_rounded:.1f} (delta {delta:+.1f})"
            )


def print_failed_recovery(failed_recovery) -> None:
    if not failed_recovery.failed_subjects:
        return

    print()
    print("What-if failed subjects were not failed (replaced by average-performance baseline):")
    print(
        f"Replacement grade used (0.5-step): {failed_recovery.replacement_grade:.1f}; "
        f"estimated CGPA gain: {failed_recovery.cgpa_gain:+.3f}"
    )
    print(
        "Projected CGPA without failed subjects: "
        f"{failed_recovery.projected_cgpa_without_failed_subjects:.3f}"
    )

    qualifies_any = any(row.qualified_now for row in failed_recovery.projected_honors)
    if qualifies_any:
        print("Result: without failed subjects, Latin honors could have been possible by CGPA.")
    else:
        print("Result: even without failed subjects, performance is still below Latin honors thresholds.")


def print_projected_honors(result) -> None:
    print("Projected honors status:")
    for row in result.projected_honors:
        if row.qualified_now:
            print(f"- Already qualified for {row.honor_name}.")
        elif row.reachable:
            print(f"- {row.honor_name}: need {row.needed_average_for_remaining_units:.3f} average in remaining units.")
        else:
            print(f"- {row.honor_name}: not reachable (needs {row.needed_average_for_remaining_units:.3f} average).")
