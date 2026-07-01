# OSS Discovery Agent

Focus: **Haitian Creole** datasets, models, repos, benchmarks, and eval tools.

## Data sources

| Category | Source |
|----------|--------|
| `datasets` | Hugging Face Hub API |
| `models` | Hugging Face Hub API |
| `repos` | GitHub Search API |
| `eval_tools` | GitHub Search API |
| `benchmarks` | Web search (Tavily / SerpAPI / Google CSE) |

## Run locally

```bash
python workflows/run_agent.py --agent oss_discovery
```

Or via API:

```bash
curl -X POST http://localhost:8000/api/agents/run/oss_discovery \
  -H "X-API-Key: $API_KEY"
```

Browse results in the dashboard at `/oss` (Recent · Reference · All tabs).

## Configuration

- **Queries:** `agents/oss_discovery/queries.yaml` — Haitian Creole search terms
- **Ranking profile:** `private/config/oss_profile.yaml` — target languages, keywords, recency rules
- **Env vars:** `GITHUB_TOKEN`, `HF_TOKEN` (optional, improves rate limits), `OSS_DISCOVERY_MAX_PER_QUERY`

## Recency (hybrid)

| Type | Ingest rule |
|------|-------------|
| `repo`, `model` | Skipped if not updated in 365 days |
| `dataset` | Always stored; recency affects score only |
| `benchmark`, `eval_tool` | Always stored (evergreen) |

Digest shows **Recent** (last 90 days) plus a **Reference benchmarks & eval tools** section for older evergreen items.

## Output

- SQLite table: `oss_resources`
- Markdown digest: `reports/oss_YYYY-MM-DD.md`

## Schedule

Weekly (recommended). Add to `.github/workflows/weekly_digest.yml` when ready.
