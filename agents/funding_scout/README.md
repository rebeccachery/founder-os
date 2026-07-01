# Funding Scout Agent

Unified morning scout across nine funding categories. Results are ranked against `private/config/founder_profile.yaml`.

## Categories

- Accelerators
- Fellowships
- Grants
- Startup competitions
- Hackathons
- Cloud credits
- University programs
- AI research funding
- Pitch competitions

## Run

```bash
python workflows/run_agent.py --agent funding_scout
```

Daily scan includes this agent. Output:

- SQLite table: `scout_opportunities`
- Markdown digest: `reports/scout_YYYY-MM-DD.md`

## Profile

Edit `private/config/founder_profile.yaml` to adjust stage, keywords, and ranking weights.
