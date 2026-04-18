from __future__ import annotations

from grades_checker.logic.terms import sort_term_labels
from grades_checker.logic.terms import parse_term_label
from grades_checker.models.entities import CourseGrade
from grades_checker.models.entities import CourseOfferingSection
from grades_checker.models.entities import EnrollmentStatus
from grades_checker.models.entities import SubjectSections


def latest_term_subject_codes(course_grades: list[CourseGrade], term_labels: list[str]) -> list[str]:
    if not course_grades:
        return []

    labels = sort_term_labels(term_labels) if term_labels else sort_term_labels(list({row.term_label for row in course_grades}))
    if not labels:
        return []

    latest_term = labels[-1]
    seen: set[str] = set()
    ordered_subjects: list[str] = []

    for row in course_grades:
        if row.term_label != latest_term:
            continue
        subject_code = row.course_code.strip().upper()
        if not subject_code or subject_code in seen:
            continue
        seen.add(subject_code)
        ordered_subjects.append(subject_code)

    return ordered_subjects


def group_sections_for_subjects(
    *,
    subject_codes: list[str],
    offerings: list[CourseOfferingSection],
    group_size: int,
) -> list[SubjectSections]:
    if group_size < 1:
        raise ValueError("group_size must be at least 1")

    normalized_subjects = [code.strip().upper() for code in subject_codes if code.strip()]
    grouped: list[SubjectSections] = []

    for subject in normalized_subjects:
        matching_sections: list[CourseOfferingSection] = []
        for section in offerings:
            if section.course_code.strip().upper() != subject:
                continue

            if section.available_slots is not None and section.available_slots < group_size:
                continue

            matching_sections.append(section)

        grouped.append(SubjectSections(subject_code=subject, sections=matching_sections))

    return grouped


def choose_offerings_term_and_year(
    *,
    enrollment_status: EnrollmentStatus,
    term_labels: list[str],
    fallback_course_grades: list[CourseGrade],
) -> tuple[int, str, bool]:
    labels = term_labels or [row.term_label for row in fallback_course_grades]
    sorted_labels = sort_term_labels(labels)

    if enrollment_status.is_regular and sorted_labels:
        latest_term_label = sorted_labels[-1]
        school_year_start, latest_term_number = parse_term_label(latest_term_label)
        if latest_term_number < 3:
            next_term_number = latest_term_number + 1
            next_school_year_start = school_year_start
        else:
            next_term_number = 1
            next_school_year_start = school_year_start + 1

        next_school_year_text = f"{next_school_year_start}{next_school_year_start + 1}"
        return next_term_number, next_school_year_text, True

    if not sorted_labels:
        raise ValueError("No term labels available for offerings fallback selection")

    latest_term_label = sorted_labels[-1]
    school_year_start, term_number = parse_term_label(latest_term_label)
    school_year_text = f"{school_year_start}{school_year_start + 1}"
    return term_number, school_year_text, False
