from collections import defaultdict

from grades_checker.logic.cgpa import compute_cgpa
from grades_checker.models.entities import ScrapedSnapshot


def run_performance_report(snapshot: ScrapedSnapshot) -> None:
    buckets: dict[str, list] = defaultdict(list)
    for row in snapshot.course_grades:
        if row.units > 0:
            buckets[row.term_label].append(row)

    print("Term performance (weighted by units):")
    for term in snapshot.term_labels:
        rows = buckets.get(term, [])
        cgpa, units = compute_cgpa(rows)
        print(f"- {term}: average {cgpa:.3f} across {units:.0f} units")
