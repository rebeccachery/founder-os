from datetime import datetime
from pathlib import Path

from lib.schemas import ExecutiveBriefing

ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = ROOT / "reports"


def write_briefing_digest(briefing: ExecutiveBriefing) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    day = briefing.briefing_date.isoformat()
    digest_path = REPORTS_DIR / f"assistant_{day}.md"

    lines = [
        f"# Executive Assistant — {day}\n\n",
        f"_Generated {briefing.generated_at.strftime('%Y-%m-%d %H:%M UTC')}_\n\n",
    ]

    lines.append("## Today's priorities\n\n")
    if briefing.priorities:
        for i, item in enumerate(briefing.priorities, 1):
            due = f" (due {item.due_at})" if item.due_at else ""
            lines.append(f"{i}. **{item.title}** [{item.category}]{due} — {item.reason}\n")
    else:
        lines.append("_No priorities flagged for today._\n")
    lines.append("\n")

    lines.append("## Potential conflicts\n\n")
    if briefing.conflicts:
        for conflict in briefing.conflicts:
            lines.append(f"- **{conflict.summary}** ({conflict.severity})\n")
    else:
        lines.append("_No scheduling conflicts detected._\n")
    lines.append("\n")

    for section_title, items in [
        ("Follow-ups", briefing.follow_ups),
        ("Deadlines", briefing.deadlines),
        ("Meetings", briefing.meetings),
        ("Applications", briefing.applications),
    ]:
        lines.append(f"## {section_title}\n\n")
        if items:
            for item in items:
                due = f" — {item.due_at}" if item.due_at else ""
                lines.append(f"- **{item.title}** ({item.category}){due}\n")
        else:
            lines.append(f"_No {section_title.lower()} in range._\n")
        lines.append("\n")

    digest_path.write_text("".join(lines))
    return digest_path
