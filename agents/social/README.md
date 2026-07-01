# Social Agent

Collects product signals and generates social content drafts.

## Phase 1 — Signal collection

- **Git commits** — local `git log` since last run (or `since_days` fallback)
- **GitHub releases & milestones** — via GitHub API when `GITHUB_TOKEN` is set
- **Features & milestones** — `config/features.yaml`
- **Datasets** — recent high-scoring rows from `oss_resources`

## Phase 2 — Content generation

- Ranks signals by post-worthiness
- Generates drafts via LLM or template fallback
- Content types: Twitter thread, LinkedIn post, demo idea, launch announcement

## LLM providers

| Provider | Cost | Setup |
|----------|------|-------|
| **ollama** (default) | Free, local OSS | `brew install ollama && ollama pull qwen2.5:7b` |
| **openai** | Paid API | Set `OPENAI_API_KEY` |
| **anthropic** | Paid API | Set `ANTHROPIC_API_KEY` |

## Config

- `config/social_profile.yaml` — repo, voice, LLM, generation thresholds
- `config/features.yaml` — manual feature narrative and roadmap milestones

## Environment

```bash
# Local OSS (default)
OLLAMA_BASE_URL=http://localhost:11434/v1
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b

# Paid alternatives
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
LLM_PROVIDER=openai   # or anthropic
LLM_MODEL=gpt-4o-mini
```

Start Ollama before running:

```bash
ollama serve          # if not already running
ollama pull qwen2.5:7b
python workflows/run_agent.py --agent social
```

Without a running LLM provider, the agent falls back to template-based drafts.

## Phase 3 — Persistent storage

Drafts are saved to the `social_posts` table in SQLite after each run. Re-running on the same day archives prior `draft` rows and inserts a fresh set.

**Statuses:** `draft` · `approved` · `posted` · `skipped` · `archived`

**API** (requires `X-API-Key`):

```bash
curl -H "X-API-Key: dev-local-key" http://localhost:8000/api/social
curl -X PATCH -H "X-API-Key: dev-local-key" -H "Content-Type: application/json" \
  -d '{"status":"approved"}' http://localhost:8000/api/social/1
```

## Run locally

```bash
python workflows/run_agent.py --agent social
```

## Output

| File | Contents |
|------|----------|
| `reports/social_context_{date}.md` | Raw signals (Phase 1) |
| `reports/social_context_{date}.json` | Structured context bundle |
| `reports/social_{date}.md` | **Content digest** — drafts + content menu |
| `reports/social_{date}.json` | Generated drafts JSON |
