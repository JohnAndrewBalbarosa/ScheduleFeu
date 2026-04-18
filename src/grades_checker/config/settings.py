from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class AppSettings:
    grades_url: str
    curriculum_url: str
    offerings_url: str
    honor_summa_min: float
    honor_summa_max: float
    honor_magna_min: float
    honor_magna_max: float
    honor_cum_min: float
    honor_cum_max: float
    outlier_method: str
    outlier_tail: str
    outlier_z_threshold: float
    baseline_estimator: str
    failed_grade_values: tuple[float, ...]
    cache_enabled: bool
    cache_file: str
    availability_cache_file: str


@dataclass(frozen=True)
class HonorRange:
    name: str
    min_gpa: float
    max_gpa: float


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _env_get(values: dict[str, str], key: str, default: str) -> str:
    return os.environ.get(key, values.get(key, default))


def _parse_float_tuple(csv_text: str) -> tuple[float, ...]:
    values: list[float] = []
    for piece in csv_text.split(","):
        item = piece.strip()
        if not item:
            continue
        values.append(float(item))
    return tuple(values)


def load_settings(env_path: str = ".env") -> AppSettings:
    file_values = _parse_env_file(Path(env_path))
    return AppSettings(
        grades_url=_env_get(file_values, "GRADES_URL", "https://solar.feutech.edu.ph/student/grades"),
        curriculum_url=_env_get(file_values, "CURRICULUM_URL", "https://solar.feutech.edu.ph/program/curriculum"),
        offerings_url=_env_get(file_values, "OFFERINGS_URL", "https://solar.feutech.edu.ph/course/offerings"),
        honor_summa_min=float(_env_get(file_values, "HONOR_SUMMA_MIN", "3.80")),
        honor_summa_max=float(_env_get(file_values, "HONOR_SUMMA_MAX", "4.00")),
        honor_magna_min=float(_env_get(file_values, "HONOR_MAGNA_MIN", "3.60")),
        honor_magna_max=float(_env_get(file_values, "HONOR_MAGNA_MAX", "3.79")),
        honor_cum_min=float(_env_get(file_values, "HONOR_CUM_MIN", "3.40")),
        honor_cum_max=float(_env_get(file_values, "HONOR_CUM_MAX", "3.59")),
        outlier_method=_env_get(file_values, "OUTLIER_METHOD", "mad").lower(),
        outlier_tail=_env_get(file_values, "OUTLIER_TAIL", "left").lower(),
        outlier_z_threshold=float(_env_get(file_values, "OUTLIER_Z_THRESHOLD", "2.5")),
        baseline_estimator=_env_get(file_values, "BASELINE_ESTIMATOR", "trimmed_mean").lower(),
        failed_grade_values=_parse_float_tuple(_env_get(file_values, "FAILED_GRADE_VALUES", "0.0,0.5")),
        cache_enabled=_env_get(file_values, "CACHE_ENABLED", "true").lower() == "true",
        cache_file=_env_get(file_values, "CACHE_FILE", ".cache/solar_data.json"),
        availability_cache_file=_env_get(file_values, "AVAILABILITY_CACHE_FILE", ".cache/availability_data.json"),
    )


def build_honor_ranges(settings: AppSettings) -> list[HonorRange]:
    return [
        HonorRange("Summa Cum Laude", settings.honor_summa_min, settings.honor_summa_max),
        HonorRange("Magna Cum Laude", settings.honor_magna_min, settings.honor_magna_max),
        HonorRange("Cum Laude", settings.honor_cum_min, settings.honor_cum_max),
    ]


def honor_targets_from_settings(settings: AppSettings) -> tuple[tuple[str, float], ...]:
    ranges = build_honor_ranges(settings)
    return tuple((item.name, item.min_gpa) for item in ranges)
