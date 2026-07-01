# Executive Assistant

Aggregates deadlines, fellowships, grants, CRM follow-ups, and launch milestones into a daily morning briefing.

## Output

- SQLite `executive_briefings` table (served via `GET /api/briefing`)
- Markdown digest at `reports/assistant_YYYY-MM-DD.md`

## Run

```bash
python workflows/run_agent.py --agent executive_assistant
```

Scheduled last in the daily pipeline so upstream agents populate data first.
