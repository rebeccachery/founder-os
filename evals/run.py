"""Evaluate scout rankers and write a markdown report.

    python -m evals.run                 # gold labels if present, else synthetic fixture
    python -m evals.run --silver        # silver labels from storage/founder_os.db
    python -m evals.run --fixture --out evals/results/fixture.md
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date
from pathlib import Path

from evals.dataset import FIXTURE_PATH, Candidate, gold_labels_path, load_jsonl, load_silver
from evals.metrics import (
    average_precision,
    bootstrap_ci,
    ndcg_at_k,
    paired_bootstrap,
    precision_at_k,
    rank_by,
    roc_auc,
)
from evals.systems import SYSTEMS
from lib.db import get_db_path
from lib.paths import ROOT
from lib.scout.profile import FounderProfile, load_founder_profile


def evaluate(
    candidates: list[Candidate],
    profile: FounderProfile,
    today: date,
    ks: tuple[int, ...] = (10, 25),
    *,
    with_ci: bool = True,
) -> tuple[list[dict], dict[str, list[float]], list[int]]:
    # Shuffle once (seeded) so ties don't inherit database insertion order —
    # curated rows were inserted later, which would otherwise leak the label.
    candidates = candidates[:]
    random.Random(7).shuffle(candidates)
    labels = [c.label for c in candidates]
    rows = []
    all_scores = {name: system(candidates, profile, today) for name, system in SYSTEMS.items()}
    for name, scores in all_scores.items():
        ranked = rank_by(scores, labels)
        row: dict = {"system": name}
        for k in ks:
            row[f"P@{k}"] = precision_at_k(ranked, k)
            row[f"nDCG@{k}"] = ndcg_at_k(ranked, k)
        row["MAP"] = average_precision(ranked)
        row["AUC"] = roc_auc(scores, labels)
        if with_ci:
            lo, hi = bootstrap_ci(scores, labels, lambda s, y: average_precision(rank_by(s, y)))
            row["MAP 95% CI"] = (lo, hi)
        rows.append(row)
    return rows, all_scores, labels


def _map(scores, labels) -> float:
    return average_precision(rank_by(scores, labels))


def paired_comparisons(all_scores: dict[str, list[float]], labels: list[int]) -> list[str]:
    names = list(all_scores)
    production, others = names[0], names[1:]
    lines = [
        "",
        f"## {production} vs. each alternative (paired bootstrap, MAP)",
        "",
        "| compared with | ΔMAP | 95% CI | P(production better) |",
        "|---|---|---|---|",
    ]
    for other in others:
        delta, (lo, hi), p_better = paired_bootstrap(all_scores[production], all_scores[other], labels, _map)
        lines.append(f"| {other} | {delta:+.3f} | {lo:+.3f} to {hi:+.3f} | {p_better:.0%} |")
    lines.append("")
    return lines


def to_markdown(rows: list[dict], *, title: str, meta: dict) -> str:
    cols = list(rows[0].keys())
    out = [f"# {title}", ""]
    out += [f"- **{k}:** {v}" for k, v in meta.items()]
    out += ["", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in rows:
        cells = []
        for col in cols:
            value = row[col]
            if isinstance(value, tuple):
                cells.append(f"{value[0]:.3f}–{value[1]:.3f}")
            elif isinstance(value, float):
                cells.append(f"{value:.3f}")
            else:
                cells.append(str(value))
        out.append("| " + " | ".join(cells) + " |")
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--labels", type=Path, help="Labeled JSONL (default: private/evals/scout_labels.jsonl)")
    source.add_argument("--silver", action="store_true", help="Silver labels from the scout database")
    source.add_argument("--fixture", action="store_true", help="Synthetic fixture (used in CI)")
    parser.add_argument("--today", type=date.fromisoformat, default=date.today(), help="As-of date for deadlines")
    parser.add_argument("--out", type=Path, help="Write the markdown report here")
    parser.add_argument("--json", type=Path, help="Write raw metrics as JSON here")
    parser.add_argument("--no-ci", action="store_true", help="Skip bootstrap confidence intervals")
    args = parser.parse_args(argv)

    if args.silver:
        db_path = get_db_path()
        candidates, label_source = load_silver(db_path), f"silver ({db_path.name})"
        profile = load_founder_profile()
    elif args.fixture or (not args.labels and not gold_labels_path().exists()):
        candidates, label_source = load_jsonl(FIXTURE_PATH), "synthetic fixture"
        profile = load_founder_profile(ROOT / "config" / "founder_profile.example.yaml")
    else:
        path = args.labels or gold_labels_path()
        candidates, label_source = load_jsonl(path), f"gold ({path.name})"
        profile = load_founder_profile()

    if not candidates:
        print("No candidates to evaluate.", file=sys.stderr)
        return 1

    n_rel = sum(1 for c in candidates if c.label >= 1)
    rows, all_scores, labels = evaluate(candidates, profile, args.today, with_ci=not args.no_ci)
    report = to_markdown(
        rows,
        title="Funding Scout ranker evaluation",
        meta={
            "labels": label_source,
            "candidates": f"{len(candidates)} ({n_rel} relevant, {n_rel / len(candidates):.0%} base rate)",
            "as-of date": args.today.isoformat(),
        },
    )
    if not args.no_ci:
        report += "\n".join(paired_comparisons(all_scores, labels))
    print(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report)
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, default=list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
