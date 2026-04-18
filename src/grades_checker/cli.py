import argparse
from grades_checker.services.analysis_flow import run_live
from grades_checker.services.analysis_flow import run_simulation
from grades_checker.services.schedule_flow import run_schedule_from_cache


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("group size must be at least 1")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check FEU Tech honors eligibility from SOLAR grades.")
    parser.add_argument("--live", action="store_true", help="Run live scrape from SOLAR using browser login.")
    parser.add_argument("--simulate-cgpa", type=float, help="Simulate honors from a known CGPA.")
    parser.add_argument("--simulate-completed-units", type=float, help="Completed units for simulation mode.")
    parser.add_argument("--simulate-total-units", type=float, default=210.0, help="Total curriculum units for simulation mode.")
    parser.add_argument("--schedule", action="store_true", help="Run schedule checker based on cached grades and live course offerings.")
    parser.add_argument("--group-size", type=_positive_int, default=1, help="Minimum available slots needed per section (default: 1).")
    parser.add_argument("--image-output", default=".cache/schedule_report.png", help="PNG path for schedule visual output.")
    parser.add_argument("--prof-excel", help="Optional XLSX file containing subject/section professor assignments.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.schedule:
        run_schedule_from_cache(
            group_size=args.group_size,
            image_output=args.image_output,
            prof_excel_path=args.prof_excel,
        )
        return

    if args.live:
        run_live()
        return

    if args.simulate_cgpa is not None and args.simulate_completed_units is not None:
        run_simulation(args.simulate_cgpa, args.simulate_completed_units, args.simulate_total_units)
        return

    raise SystemExit(
        "Use --live for scraping, or pass --simulate-cgpa and --simulate-completed-units for calculations."
    )


if __name__ == "__main__":
    main()
