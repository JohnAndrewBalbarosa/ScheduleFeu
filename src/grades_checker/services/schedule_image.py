from __future__ import annotations

from pathlib import Path

from grades_checker.models.entities import SubjectSections


def render_schedule_png(
    *,
    grouped: list[SubjectSections],
    snapshot_time: str,
    target_subject_codes: list[str],
    group_size: int,
    output_path: str,
) -> str:
    try:
        from PIL import Image
        from PIL import ImageDraw
        from PIL import ImageFont
    except Exception:
        return ""

    width = 1750
    margin = 24
    header_height = 130
    row_height = 36
    subject_title_height = 38

    row_count = sum(max(1, len(item.sections)) for item in grouped)
    subject_count = len(grouped)
    height = header_height + subject_count * subject_title_height + row_count * row_height + margin * 2 + 40

    image = Image.new("RGB", (width, max(height, 280)), "#f6f8fb")
    draw = ImageDraw.Draw(image)

    font = ImageFont.load_default()
    bold_font = ImageFont.load_default()

    # Header block
    draw.rectangle([(margin, margin), (width - margin, margin + 90)], fill="#0f172a")
    draw.text((margin + 16, margin + 10), "FEU Tech Schedule Availability", fill="#ffffff", font=bold_font)
    draw.text((margin + 16, margin + 34), f"Generated from cache: {snapshot_time}", fill="#dbeafe", font=font)
    draw.text((margin + 16, margin + 52), f"Group size: {group_size}", fill="#dbeafe", font=font)
    draw.text((margin + 260, margin + 52), f"Subjects: {', '.join(target_subject_codes)}", fill="#dbeafe", font=font)

    x_subject = margin + 12
    x_section = margin + 170
    x_day = margin + 315
    x_time = margin + 405
    x_room = margin + 700
    x_professor = margin + 900
    x_class_size = margin + 1240
    x_available = margin + 1380

    y = margin + 104

    for item in grouped:
        draw.rectangle([(margin, y), (width - margin, y + subject_title_height - 2)], fill="#dbeafe")
        draw.text((x_subject, y + 11), item.subject_code, fill="#1e3a8a", font=bold_font)
        draw.text((x_section, y + 11), "Section", fill="#1e3a8a", font=bold_font)
        draw.text((x_day, y + 11), "Day", fill="#1e3a8a", font=bold_font)
        draw.text((x_time, y + 11), "Time", fill="#1e3a8a", font=bold_font)
        draw.text((x_room, y + 11), "Room", fill="#1e3a8a", font=bold_font)
        draw.text((x_professor, y + 11), "Professor", fill="#1e3a8a", font=bold_font)
        draw.text((x_class_size, y + 11), "Class Size", fill="#1e3a8a", font=bold_font)
        draw.text((x_available, y + 11), "Available", fill="#1e3a8a", font=bold_font)
        y += subject_title_height

        rows = item.sections if item.sections else [None]
        for section in rows:
            draw.rectangle([(margin, y), (width - margin, y + row_height - 2)], fill="#ffffff")
            draw.line([(margin, y + row_height - 2), (width - margin, y + row_height - 2)], fill="#e5e7eb", width=1)

            if section is None:
                draw.text((x_section, y + 10), "No matching sections", fill="#991b1b", font=font)
            else:
                class_size_text = "unknown" if section.class_size is None else str(section.class_size)
                available_text = "unknown" if section.available_slots is None else str(section.available_slots)
                draw.text((x_section, y + 10), section.section_code, fill="#111827", font=font)
                draw.text((x_day, y + 10), section.day or "-", fill="#111827", font=font)
                draw.text((x_time, y + 10), section.time or "-", fill="#111827", font=font)
                draw.text((x_room, y + 10), section.room or "-", fill="#111827", font=font)
                draw.text((x_professor, y + 10), section.professor_name or "-", fill="#111827", font=font)
                draw.text((x_class_size, y + 10), class_size_text, fill="#111827", font=font)
                draw.text((x_available, y + 10), available_text, fill="#111827", font=font)

            y += row_height

        y += 8

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG")
    return str(destination)
