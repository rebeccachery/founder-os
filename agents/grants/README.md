# Grants Agent

Discovers grant programs via search APIs and upserts into the `grants` table.

## Run locally

```bash
python workflows/run_agent.py --agent grants
```

## Output

- Table: `grants`
- Dashboard: `/grants`, `/deadlines`
