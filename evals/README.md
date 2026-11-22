# Ranker evaluation

Funding Scout ranks hundreds of search hits each night, and the dashboard only
shows the top of that list. Whether the ranker works is a question the data can
answer, so this harness answers it.

```bash
make eval            # gold labels if you have them, else the synthetic fixture
make eval-silver     # silver labels from your local scout database
make label           # hand-label opportunities for the gold set (about 15 min for 60)
```

## What's measured

| Metric | Why it's here |
|---|---|
| **P@10, nDCG@10** | The dashboard and digest show about 10 items. This is what you actually see. |
| **P@25, nDCG@25** | A deeper look at the list, for when you scroll. |
| **MAP** | One number covering the whole ranking. Penalizes burying good items anywhere. |
| **AUC** | The chance that a relevant item outscores an irrelevant one. Doesn't depend on the base rate. |
| **Bootstrap CI** | 1,000 resamples of the items. With 40 positives, single numbers are noisy. |
| **Paired bootstrap Δ** | Each system against production on the *same* resamples. Two systems' separate CIs can overlap even when one wins on nearly every resample. |

Ties are broken by a seeded shuffle, not by database order. Curated rows were
inserted later, so ordering by row id would quietly leak the label.

## Systems

| System | What it is |
|---|---|
| `keyword_v1` | The original ranker: weighted keyword signals, **substring** matching |
| `keyword_v2` | Whole-word matching ([`lib/text.py`](../lib/text.py)) |
| `keyword_v3` | v2 plus a title actionability penalty ([`lib/scout/actionability.py`](../lib/scout/actionability.py)). **Production.** |
| `bm25` | Okapi BM25 with the founder profile as the query. The standard lexical baseline. |
| `deadline_only` | Ranks by deadline urgency alone |
| `random` | Seeded random. Any system has to beat this. |

## Labels

- **Gold**: hand labels (0 = not relevant, 1 = worth a look, 2 = would apply),
  sampled evenly from the top, middle and bottom thirds of the production ranking
  so the set can catch good items the ranker buried, not just bad items at the top.
  Stored in `private/evals/` (gitignored) because they record one founder's judgments.
- **Silver**: the 40 opportunities a human saved or a verification pass confirmed
  are positives. The 488 raw search hits are treated as negatives, but some of
  them are good listings, so silver numbers *understate* every system. Use them
  to compare systems, not as absolute quality.
- **Fixture**: 30 synthetic listings in [`fixtures/`](fixtures/), including
  substring traps ("email", "said", "maintain"), so CI can run the harness end to
  end. It's a smoke test only. The numbers on it mean nothing.

## Results: silver labels, 528 opportunities (2026-11-20)

Full report: [`results/silver_2026-11-20.md`](results/silver_2026-11-20.md)

| System | P@10 | MAP | AUC |
|---|---|---|---|
| keyword_v3 (production) | **0.30** | **0.138** | **0.604** |
| keyword_v2 (word match) | 0.10 | 0.115 | 0.581 |
| keyword_v1 (substring) | 0.00 | 0.092 | 0.551 |
| bm25 (profile query) | 0.10 | 0.073 | 0.443 |
| random | 0.20 | 0.104 | 0.544 |

Paired bootstrap, production vs.: v2 **+0.022 MAP** (95% CI +0.008 to +0.065),
v1 **+0.046** (+0.019 to +0.112), BM25 **+0.065** (+0.021 to +0.150). Each
change is a reliable improvement over the version before it. Against random,
the gain is +0.034 but the CI crosses zero (−0.021 to +0.125).

### What the numbers say

1. **Substring matching was a real bug.** On the live corpus, `"AI"` matched
   322 listings as a substring but only 172 as a word. The other 150 were
   "email", "said", "maintain" and similar. Whole-word matching fixed it.
2. **The top of the list was full of pages *about* opportunities.** Error
   analysis on v2's top 12: listicles ("Top 26 Language Learning Startups to
   Watch"), press releases ("… Announces 2014 Class") and past cycles. They are
   on-topic, so keyword relevance can't separate them out. None of the 40
   curated positives match these title patterns, while 14% of raw hits (69 of 488)
   do. v3 discounts them, and P@10 rises from 0.1 to 0.3.
3. **Topical relevance isn't enough, and the ranker isn't reliably better than
   random yet.** BM25 does *worse* than random (AUC 0.44). The most on-topic
   pages are articles, not application pages. What makes a result good here is
   mostly "is this an open program I can apply to", not how well it matches the
   topic.

### Caveats

- The v3 rules came from error analysis on the same silver set they're scored
  on, so the v2 → v3 gain is optimistic. Gold labels are the held-out check.
- Silver positives have shorter snippets than raw hits (median 243 vs. 500
  characters). That makes them look worse to any keyword method.
- One known miss: "Top EdTech Accelerators & Incubators for Startups (2026)"
  has no number after "Top", so it isn't discounted. I left the rule as is
  rather than overfit it.

## Next steps

1. **Gold labels** (`make label`): 60–100 stratified items, enough to confirm
   or reject the v3 gain.
2. **Page-type classifier.** Finding 3 says actionability is the main signal.
   Train a small logistic regression on title and URL features plus the
   provider's relevance score, using gold labels, and compare it to the
   hand-written rules.
3. **Embedding relevance.** Swap the keyword signals for cosine similarity
   between the profile and the listing (a small sentence-embedding model run
   locally), and measure whether it beats v3 on gold labels.
4. **LLM re-ranking of the top 25.** Have an LLM judge "is this an open
   application page?" for the 25 items shown, and measure the P@10 lift
   against its cost.
