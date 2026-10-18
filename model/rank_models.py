
#!/usr/bin/env python3

import argparse
import json
import math
import statistics
from pathlib import Path


DEFAULT_DIR = Path("benchmark_results")

# Weights for the final score. They are normalized automatically.
WEIGHTS = {
    "request_success_rate": 0.10,
    "valid_json_rate": 0.10,
    "schema_compliance_rate": 0.10,
    "correct_count_rate": 0.15,
    "all_names_unique_batch_rate": 0.10,
    "length_compliance_rate": 0.10,
    "keyword_relevance_rate": 0.05,
    "pronounceability_rate": 0.10,
    "pairwise_diversity": 0.10,
    "speed_score": 0.10,
}

# Models failing these gates are ineligible to win.
MIN_REQUEST_SUCCESS = 0.95
MIN_JSON_RATE = 0.95
MIN_SCHEMA_RATE = 0.95
MIN_COUNT_RATE = 0.90
MIN_LENGTH_RATE = 0.90

# Latency at or below this earns a full speed score.
# Adjust this to your product's actual latency target.
TARGET_LATENCY_SECONDS = 3.0


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Skipping {path}: {exc}")
        return None


def numeric(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def mean(values):
    values = [v for v in values if numeric(v)]
    return statistics.mean(values) if values else None


def rate(value):
    return value if numeric(value) else None


def speed_score(latency):
    if not numeric(latency) or latency <= 0:
        return 0.0
    return min(1.0, TARGET_LATENCY_SECONDS / latency)


def aggregate_runs(model_name, runs):
    """Aggregate run-level records across benchmark files."""
    if not runs:
        return None

    total = len(runs)
    successful = [r for r in runs if r.get("success") is True]

    def success_rate(predicate):
        return sum(bool(predicate(r)) for r in runs) / total

    def successful_mean(key):
        return mean([r.get(key) for r in successful])

    # The benchmark records per-run length/relevance/diversity rates.
    metrics = {
        "model": model_name,
        "runs": total,
        "successful_requests": len(successful),
        "request_success_rate": len(successful) / total,
        "valid_json_rate": success_rate(
            lambda r: r.get("success") is True
            and r.get("parse_ok") is True
        ),
        "schema_compliance_rate": success_rate(
            lambda r: r.get("success") is True
            and r.get("schema_ok") is True
        ),
        "correct_count_rate": success_rate(
            lambda r: r.get("success") is True
            and r.get("count_correct") is True
        ),
        "all_names_unique_batch_rate": success_rate(
            lambda r: r.get("success") is True
            and r.get("all_names_unique") is True
        ),
        "length_compliance_rate": successful_mean(
            "length_compliance_rate"
        ),
        "keyword_relevance_rate": successful_mean(
            "keyword_relevance_rate"
        ),
        "pronounceability_rate": successful_mean(
            "pronounceability_rate"
        ),
        "pairwise_diversity": successful_mean("pairwise_diversity"),
        "mean_latency_seconds": successful_mean("latency_seconds"),
        "p95_latency_seconds": None,
        "mean_generation_tokens_per_second": successful_mean(
            "generation_tokens_per_second"
        ),
    }

    latencies = [
        r["latency_seconds"]
        for r in successful
        if numeric(r.get("latency_seconds"))
    ]
    if latencies:
        ordered = sorted(latencies)
        index = 0.95 * (len(ordered) - 1)
        lower = math.floor(index)
        upper = math.ceil(index)
        metrics["p95_latency_seconds"] = (
            ordered[lower]
            if lower == upper
            else ordered[lower] * (upper - index)
            + ordered[upper] * (index - lower)
        )

    # Keep the benchmark's composite score out of this calculation:
    # rank from the underlying metrics to make the weighting explicit.
    latency = metrics["mean_latency_seconds"]
    metrics["speed_score"] = speed_score(latency)

    return metrics


def is_eligible(metrics):
    gates = {
        "request_success_rate": MIN_REQUEST_SUCCESS,
        "valid_json_rate": MIN_JSON_RATE,
        "schema_compliance_rate": MIN_SCHEMA_RATE,
        "correct_count_rate": MIN_COUNT_RATE,
        "length_compliance_rate": MIN_LENGTH_RATE,
    }

    failures = []
    for key, threshold in gates.items():
        value = metrics.get(key)
        if not numeric(value) or value < threshold:
            shown = "N/A" if value is None else f"{value:.1%}"
            failures.append(
                f"{key}={shown} (minimum {threshold:.0%})"
            )

    return not failures, failures


def calculate_score(metrics):
    """Weighted score from 0 to 100, renormalizing missing metrics."""
    weighted_total = 0.0
    available_weight = 0.0

    for key, weight in WEIGHTS.items():
        value = metrics.get(key)
        if not numeric(value):
            continue

        # Clip all metrics to [0, 1].
        value = max(0.0, min(1.0, value))
        weighted_total += value * weight
        available_weight += weight

    if available_weight == 0:
        return None

    return 100 * weighted_total / available_weight


def load_benchmarks(directory):
    files = sorted(directory.glob("benchmark_*.json"))
    if not files:
        raise SystemExit(
            f"No benchmark_*.json files found in {directory.resolve()}"
        )

    # Store every run so repeated benchmark files contribute to the
    # aggregate, rather than treating each file's summary as one run.
    runs_by_model = {}
    metadata_by_model = {}

    for path in files:
        data = read_json(path)
        if not isinstance(data, dict):
            continue

        models = data.get("models", {})
        if not isinstance(models, dict):
            print(f"Skipping unexpected model structure in {path}")
            continue

        for model_name, model_data in models.items():
            runs = model_data.get("runs", [])
            if not isinstance(runs, list):
                continue

            runs_by_model.setdefault(model_name, []).extend(runs)
            metadata_by_model.setdefault(model_name, []).append({
                "file": str(path),
                "timestamp": data.get("metadata", {}).get("timestamp_utc"),
                "strategy": data.get("metadata", {}).get("strategy"),
                "count": data.get("metadata", {}).get("count"),
                "temperature": data.get("metadata", {}).get("temperature"),
            })

    return runs_by_model, metadata_by_model, files


def fmt_pct(value):
    return f"{value:.1%}" if numeric(value) else "N/A"


def fmt_num(value, digits=2):
    return f"{value:.{digits}f}" if numeric(value) else "N/A"


def main():
    global TARGET_LATENCY_SECONDS
    
    parser = argparse.ArgumentParser(
        description="Rank models from saved naming benchmark JSON files."
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_DIR,
        help="Directory containing benchmark_*.json files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark_results/ranking.json"),
        help="Path for the ranking report.",
    )
    parser.add_argument(
        "--target-latency",
        type=float,
        default=TARGET_LATENCY_SECONDS,
        help="Latency in seconds that earns a full speed score.",
    )
    args = parser.parse_args()

    
    if args.target_latency <= 0:
        parser.error("--target-latency must be positive.")
    TARGET_LATENCY_SECONDS = args.target_latency

    runs_by_model, metadata_by_model, files = load_benchmarks(args.dir)

    ranked = []
    for model_name, runs in runs_by_model.items():
        metrics = aggregate_runs(model_name, runs)
        if metrics is None:
            continue

        eligible, failures = is_eligible(metrics)
        metrics["eligible"] = eligible
        metrics["eligibility_failures"] = failures
        metrics["score"] = calculate_score(metrics)
        metrics["source_runs"] = metadata_by_model[model_name]
        ranked.append(metrics)

    # Eligible models always rank above ineligible models.
    ranked.sort(
        key=lambda m: (
            m["eligible"],
            m["score"] if m["score"] is not None else -1,
        ),
        reverse=True,
    )

    print(f"\nRead {len(files)} benchmark files.")
    print(f"Found {len(ranked)} model(s).\n")

    headers = [
        ("rank", "#", 3),
        ("model", "Model", 36),
        ("eligible", "Eligible", 8),
        ("score", "Score", 7),
        ("request_success_rate", "Success", 8),
        ("schema_compliance_rate", "Schema", 8),
        ("correct_count_rate", "Count", 8),
        ("length_compliance_rate", "Length", 8),
        ("pairwise_diversity", "Diversity", 9),
        ("mean_latency_seconds", "Mean s", 8),
        ("p95_latency_seconds", "P95 s", 8),
        ("mean_generation_tokens_per_second", "Tok/s", 8),
    ]

    def value_for(row, key):
        if key == "rank":
            return str(row["rank"])
        if key == "model":
            return row["model"]
        if key == "eligible":
            return "YES" if row["eligible"] else "NO"
        if key == "score":
            return fmt_num(row["score"])
        if key.endswith("_rate"):
            return fmt_pct(row.get(key))
        if key in ("pairwise_diversity",):
            return fmt_num(row.get(key), 3)
        return fmt_num(row.get(key))

    widths = {
        key: max(width, len(label))
        for key, label, width in headers
    }

    print(" | ".join(label.ljust(widths[key]) for key, label, _ in headers))
    print("-+-".join("-" * widths[key] for key, _, _ in headers))

    for i, row in enumerate(ranked, start=1):
        row["rank"] = i
        print(" | ".join(
            value_for(row, key).ljust(widths[key])
            for key, _, _ in headers
        ))

        if not row["eligible"]:
            print("    Rejected: " + "; ".join(row["eligibility_failures"]))

    eligible_models = [m for m in ranked if m["eligible"] and m["score"] is not None]
    winner = eligible_models[0] if eligible_models else None

    if winner:
        print(f"\nBEST MODEL: {winner['model']}")
        print(f"Weighted score: {winner['score']:.2f}/100")
        print(
            f"Mean latency: {fmt_num(winner['mean_latency_seconds'])} s | "
            f"P95: {fmt_num(winner['p95_latency_seconds'])} s"
        )
    else:
        print(
            "\nNo model passed all reliability gates. "
            "Fix output reliability before choosing a winner."
        )

    report = {
        "ranking_timestamp_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "benchmark_files": [str(p) for p in files],
        "settings": {
            "weights": WEIGHTS,
            "minimum_gates": {
                "request_success_rate": MIN_REQUEST_SUCCESS,
                "valid_json_rate": MIN_JSON_RATE,
                "schema_compliance_rate": MIN_SCHEMA_RATE,
                "correct_count_rate": MIN_COUNT_RATE,
                "length_compliance_rate": MIN_LENGTH_RATE,
            },
            "target_latency_seconds": TARGET_LATENCY_SECONDS,
        },
        "winner": winner["model"] if winner else None,
        "models": ranked,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Detailed ranking saved to: {args.output}")


if __name__ == "__main__":
    main()
