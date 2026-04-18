from __future__ import annotations


def parse_term_label(term_label: str) -> tuple[int, int]:
    """Parse labels like '2 - 20252026' into (2025, 2)."""
    left, right = [piece.strip() for piece in term_label.split("-", maxsplit=1)]
    term_number = int(left)
    school_year_text = right
    school_year_start = int(school_year_text[:4])
    return school_year_start, term_number


def sort_term_labels(term_labels: list[str]) -> list[str]:
    return sorted(term_labels, key=parse_term_label)
