# Social Agent

Collects product signals from **Your Company repos** and generates social content drafts.

## Watched repos

| Repo | Role | Local path | Commit detail |
|------|------|------------|-----------------|
| `your-product-repo` | Primary (private) | `../your-product-repo` | Subjects only |
| `nyc_map` | Showcase | `../nyc-map` | Subject + sanitized body |
| `your-product-demo` | Showcase | `../your-product-demo` | Subject + sanitized body |

`founder-os` is excluded from social signals.

## Setup

Clone repos as siblings of `founder-os`:

```
~/Desktop/work/
  founder-os/
  your-product-repo/
  nyc-map/
  your-product-demo/
```

Optional path overrides in `.env`:

```bash
PRODUCT_REPO_PATH=../your-product-repo
NYC_MAP_PATH=../nyc-map
DEMO_REPO_PATH=../your-product-demo
GITHUB_TOKEN=ghp_...   # required for private repo via API
```

## Run

```bash
python workflows/run_agent.py --agent social
```

## Output

- `reports/social_context_{date}.md` — signals grouped by repo
- `reports/social_{date}.md` — Your Company content drafts
- `social_posts` table + `/social` dashboard

CTA: https://example.com/
