"""Hand-label scout opportunities for the gold evaluation set.

    python -m evals.label            # label 60 items (resumable; Ctrl-C saves progress)
    python -m evals.label --n 100

Sampling is stratified across the production score distribution (top, middle
and bottom thirds). Labeling only the top of the ranking would measure
precision but hide everything the ranker wrongly buried.

Keys: 2 = would apply · 1 = worth a look · 0 = not relevant · s = skip · q = quit
"""

from __future__ import annotations

import argparse
import random
import textwrap
from pathlib import Path

from evals.dataset import Candidate, gold_labels_path, load_jsonl, unlabeled_from_db
from lib.db import get_db_path


def stratified_sample(pool: list[tuple[Candidate, float]], n: int, seed: int = 13) -> list[Candidate]:
    rng = random.Random(seed)
    ordered = [c for c, _ in sorted(pool, key=lambda item: -item[1])]
    thirds = [ordered[i::3] for i in range(3)] if len(ordered) < 3 else [
        ordered[: len(ordered) // 3],
        ordered[len(ordered) // 3 : 2 * len(ordered) // 3],
        ordered[2 * len(ordered) // 3 :],
    ]
    picks: list[Candidate] = []
    for bucket in thirds:
        rng.shuffle(bucket)
        picks.extend(bucket[: n // 3])
    rng.shuffle(picks)  # don't show items in score order — that anchors the labeler
    return picks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, default=60)
    parser.add_argument("--out", type=Path, default=gold_labels_path())
    args = parser.parse_args(argv)

    done = {c.id for c in load_jsonl(args.out)} if args.out.exists() else set()
    pool = [(c, s) for c, s in unlabeled_from_db(get_db_path()) if c.id not in done]
    todo = stratified_sample(pool, max(0, args.n - len(done)))
    if not todo:
        print(f"Nothing to label — {len(done)} labels already in {args.out}")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    print(__doc__.split("Keys:")[1].strip())
    labeled = 0
    with args.out.open("a") as f:
        for i, cand in enumerate(todo, 1):
            print(f"\n[{len(done) + i}/{args.n}] {cand.category.replace('_', ' ')}"
                  f"{' · deadline ' + cand.deadline_at.isoformat() if cand.deadline_at else ''}")
            print(f"  {cand.title}")
            print(textwrap.indent(textwrap.fill(cand.snippet[:400], 90), "  "))
            while (key := input("  label> ").strip().lower()) not in {"0", "1", "2", "s", "q"}:
                pass
            if key == "q":
                break
            if key == "s":
                continue
            cand.label = int(key)
            f.write(cand.to_json() + "\n")
            f.flush()
            labeled += 1
    print(f"\nSaved {labeled} new labels → {args.out}  (total {len(done) + labeled})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
