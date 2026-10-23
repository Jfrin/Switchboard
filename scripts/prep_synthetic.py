"""Turn the big synthetic dataset into a deduped, seeded dev/test split.

    docker compose run --rm api python scripts/prep_synthetic.py
    docker compose run --rm api python scripts/prep_synthetic.py --n 150 --seed 3

Reads eval/synthetic_dataset.json (JSON Lines: one email per line) and writes
eval/synthetic_dev.jsonl and eval/synthetic_test.jsonl. Tune prompts and rules on
dev; run the test file once at the end and report that number.

Steps: drop empty/duplicate emails, repair sender addresses, cap how often one company
appears (the mock-enrichment domains acme.com and bigcorp.com repeat a lot), take a
sample stratified by expected team, then split it stratified by team.
"""

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

EVAL = Path(__file__).resolve().parent.parent / "eval"


def load(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("["):  # tolerate a plain JSON array too
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def clean(rows: list[dict], max_per_company: int) -> tuple[list[dict], Counter]:
    dropped: Counter = Counter()
    seen: set[str] = set()
    per_company: Counter = Counter()
    kept = []
    for row in rows:
        if not all(k in row for k in ("from", "subject", "body", "expected")):
            dropped["missing fields"] += 1
            continue
        if not row["body"].strip():
            dropped["empty body"] += 1
            continue
        key = re.sub(r"\s+", " ", row["body"]).strip().lower()
        if key in seen:
            dropped["duplicate body"] += 1
            continue
        company = row["expected"].get("company")
        if company and per_company[company] >= max_per_company:
            dropped[f"company over cap ({max_per_company})"] += 1
            continue
        seen.add(key)
        if company:
            per_company[company] += 1
        row = {**row, "from": re.sub(r"\s+", "", row["from"])}  # "a@b c.com" -> "a@bc.com"
        kept.append(row)
    return kept, dropped


def stratified_take(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Take n rows keeping each team's share of the data."""
    by_team: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_team[row["expected"]["team"]].append(row)
    if n >= len(rows):
        return list(rows)
    picked = []
    for team in sorted(by_team):
        group = by_team[team]
        rng.shuffle(group)
        picked += group[: max(1, round(n * len(group) / len(rows)))]
    rng.shuffle(picked)
    return picked[:n]


def split(rows: list[dict], test_frac: float, rng: random.Random):
    by_team: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_team[row["expected"]["team"]].append(row)
    dev, test = [], []
    for team in sorted(by_team):
        group = by_team[team]
        rng.shuffle(group)
        cut = round(len(group) * test_frac)
        test += group[:cut]
        dev += group[cut:]
    rng.shuffle(dev)
    rng.shuffle(test)
    return dev, test


def write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")


def summary(name: str, rows: list[dict]) -> None:
    teams = Counter(r["expected"]["team"] for r in rows)
    intents = Counter(r["expected"]["intent"] for r in rows)
    print(f"{name}: {len(rows)} rows | teams {dict(teams)} | intents {dict(intents)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="default: eval/synthetic_dataset.jsonl or .json")
    ap.add_argument("--n", type=int, default=200, help="total rows to sample")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--test-frac", type=float, default=0.3)
    ap.add_argument("--max-per-company", type=int, default=5)
    args = ap.parse_args()

    if args.input:
        source = Path(args.input)
    else:
        candidates = [EVAL / "synthetic_dataset.jsonl", EVAL / "synthetic_dataset.json"]
        source = next((p for p in candidates if p.exists()), None)
        if source is None:
            raise SystemExit("put your file at eval/synthetic_dataset.jsonl (or pass --input)")

    rng = random.Random(args.seed)
    raw = load(source)
    rows, dropped = clean(raw, args.max_per_company)
    print(f"loaded {len(raw)}, kept {len(rows)} after cleaning; dropped: {dict(dropped)}")

    sample = stratified_take(rows, args.n, rng)
    dev, test = split(sample, args.test_frac, rng)
    write(EVAL / "synthetic_dev.jsonl", dev)
    write(EVAL / "synthetic_test.jsonl", test)
    summary("dev ", dev)
    summary("test", test)


if __name__ == "__main__":
    main()
