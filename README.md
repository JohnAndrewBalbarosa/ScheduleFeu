# ScheduleFeu

## Overview

Smart schedule availability checker for FEU Tech SOLAR

Repository: [JohnAndrewBalbarosa/ScheduleFeu](https://github.com/JohnAndrewBalbarosa/ScheduleFeu)

## Problem and Goal

**Problem.** FEU Tech students must compare many SOLAR schedules manually to find common availability while avoiding class conflicts.

**Goal.** Collect schedule data, calculate conflict-free group availability, and export a shareable visual report.

## System Design

- `src/`: Python package for SOLAR collection, schedule normalization, conflict analysis, and reporting.
- Playwright: rendered-page access and schedule extraction.
- Pillow: PNG report generation; OpenPyXL: optional workbook mappings; Rich: CLI output.

## Setup and Usage

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# Inspect available commands
python -m grades_checker.cli --help
```

## Evaluation Method

- Define the project task and expected behavior.
- Run representative examples or user flows.
- Record correctness, speed, reliability, usability, and failure cases.

## Results

- No validated quantitative results are published yet.
- Current README status: implementation and usage are documented before formal measurement.

## Interpretation

- The project can be described as implemented or in progress, but impact claims should stay limited until measurements are collected.
- Use the evaluation plan below to turn the project into resume-ready, evidence-backed work.

## Limitations

- Results should only be treated as validated when this README includes the dataset, sample size, metric definition, and reproduction steps.
- Any AI-generated, OCR-based, scraped, or heuristic output requires manual review before being used as ground truth.
- Environment-dependent measurements such as latency, memory use, browser behavior, and API reliability should be re-measured on the target machine.

## Recommendations and Future Work

- Number of schedules tested.
- Conflict-detection accuracy.
- Time saved compared with manual schedule checking.

## Documentation Standard

This README follows a technical-project structure: overview, goal, system design, setup, evaluation method, results, interpretation, limitations, and recommendations. Update the Results section whenever new measurements are available so project claims stay evidence-backed.
