# Social Agent

Collects product signals from configured repos and generates social content drafts.

## Configuration

Repo list and voice settings live in `private/config/social_profile.yaml` (copy from [config/social_profile.example.yaml](../../config/social_profile.example.yaml)).

## Setup

Clone product repos as siblings of `founder-os`, or set path overrides in `.env`:

```bash
PRODUCT_REPO_PATH=../your-product-repo
SHOWCASE_REPO_PATH=../your-showcase-repo
DEMO_REPO_PATH=../your-product-demo
GITHUB_TOKEN=ghp_...   # required for private repos via API
```

## Run

```bash
python workflows/run_agent.py --agent social
```

## Output

- `reports/social_context_{date}.md` — signals grouped by repo
- `reports/social_{date}.md` — content drafts
- `social_posts` table + `/social` dashboard

CTA URL comes from `private/config/social_profile.yaml` (`voice.cta_url`).
