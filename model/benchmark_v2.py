import json
import os
import re
import statistics
import sys
import time
from datetime import UTC, datetime, timezone

import requests
from templates_v2 import BalancedStrategy

# ============================================================
# Configuration
# ============================================================

if len(sys.argv) < 2:
    sys.exit("Usage: python3 benchmark.py <model-name> [--runs 10] [--warmup 1]")

MODEL_NAME = sys.argv[1]


def cli_int(flag, default):
    if flag not in sys.argv:
        return default

    try:
        value = int(sys.argv[sys.argv.index(flag) + 1])
        if value < 0:
            raise ValueError
        return value
    except (ValueError, IndexError):
        sys.exit(f"{flag} requires a non-negative integer")


RUNS = cli_int("--runs", 10)
WARMUP_RUNS = cli_int("--warmup", 1)

TEMPERATURE = 0.7
API_URL = "http://127.0.0.1:8080/v1/chat/completions"
RESULTS_FILE = "benchmark_results_v2.json"
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 120

COUNT = 10
PRODUCT_DESCRIPTION = (
    "An AI-powered name generator for software products "
    "that checks domain and GitHub availability."
)
KEYWORDS = "forge, mint, craft, syntax, token, nym, moniker, alias"


# ============================================================
# Strategy and payload
# ============================================================

STRATEGY = BalancedStrategy()
MAX_LENGTH = STRATEGY.MAX_LENGTH


def get_payload(strategy):
    schema = {
        "name": "product_names",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "product_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        f"Exactly {COUNT} unique software product names "
                        f"shorter than {MAX_LENGTH} characters."
                    ),
                }
            },
            "required": ["product_names"],
            "additionalProperties": False,
        },
    }

    return {
        "model": MODEL_NAME,
        "temperature": TEMPERATURE,
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": schema,
        },
        "messages": [
            {
                "role": "system",
                "content": strategy.SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": strategy.get_user_prompt(
                    COUNT,
                    PRODUCT_DESCRIPTION,
                    KEYWORDS,
                ),
            },
        ],
    }


# ============================================================
# Quality metrics
# ============================================================


def normalize_name(name):
    # Treat whitespace and capitalization differences as duplicates.
    return re.sub(r"\s+", "", name).casefold()


def evaluate_quality(raw_content, strategy):
    max_length = strategy.MAX_LENGTH

    quality = {
        "valid_json": False,
        "correct_schema": False,
        "names_extracted": [],
        "count_match": False,
        "all_unique": False,
        "all_under_max_length": False,
        "valid_name_rate": 0.0,
        "unique_rate": 0.0,
        "length_compliance_rate": 0.0,
        "keyword_relevance": 0.0,
        "average_length": 0.0,
        "invalid_name_count": 0,
    }

    try:
        parsed = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError):
        return quality

    if not isinstance(parsed, dict):
        return quality

    quality["valid_json"] = True

    names = parsed.get("product_names")
    if not isinstance(names, list):
        return quality

    quality["correct_schema"] = set(parsed.keys()) == {"product_names"} and all(
        isinstance(name, str) for name in names
    )
    quality["names_extracted"] = names
    quality["count_match"] = len(names) == COUNT

    if not names:
        return quality

    valid_names = [
        name for name in names if isinstance(name, str) and bool(name.strip())
    ]

    quality["invalid_name_count"] = len(names) - len(valid_names)
    quality["valid_name_rate"] = round(len(valid_names) / len(names), 4)

    normalized = [normalize_name(name) for name in valid_names]

    quality["unique_rate"] = round(len(set(normalized)) / len(names), 4)
    quality["all_unique"] = len(valid_names) == len(names) and len(
        set(normalized)
    ) == len(names)

    compliant = [name for name in valid_names if len(name) < max_length]

    quality["length_compliance_rate"] = round(len(compliant) / len(names), 4)
    quality["all_under_max_length"] = len(valid_names) == len(names) and len(
        compliant
    ) == len(names)

    if valid_names:
        quality["average_length"] = round(
            statistics.mean(len(name) for name in valid_names),
            2,
        )

        keywords = [
            keyword.strip().casefold()
            for keyword in KEYWORDS.split(",")
            if keyword.strip()
        ]

        quality["keyword_relevance"] = round(
            sum(any(k in name.casefold() for k in keywords) for name in valid_names)
            / len(valid_names),
            4,
        )

    return quality


# ============================================================
# Performance metrics
# ============================================================


def extract_performance(data, elapsed_sec):
    usage = data.get("usage") or {}
    timings = data.get("timings") or {}

    completion_tokens = usage.get("completion_tokens") or 0
    prompt_tokens = usage.get("prompt_tokens") or 0

    generation_ms = timings.get("predicted_ms")
    generation_sec = (
        generation_ms / 1000
        if isinstance(generation_ms, (int, float)) and generation_ms > 0
        else None
    )

    generation_tps = timings.get("predicted_per_second")

    if generation_tps is None and generation_sec:
        generation_tps = completion_tokens / generation_sec

    prompt_ms = timings.get("prompt_ms")
    prompt_tps = timings.get("prompt_per_second")

    return {
        "end_to_end_sec": round(elapsed_sec, 4),
        "generation_sec": (
            round(generation_sec, 4) if generation_sec is not None else None
        ),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": usage.get(
            "total_tokens",
            prompt_tokens + completion_tokens,
        ),
        "end_to_end_tokens_per_sec": round(completion_tokens / elapsed_sec, 2)
        if elapsed_sec > 0
        else 0,
        "generation_tokens_per_sec": (
            round(generation_tps, 2)
            if isinstance(generation_tps, (int, float))
            else None
        ),
        "prompt_tokens_per_sec": prompt_tps,
        "prompt_processing_ms": prompt_ms,
        "server_generation_ms": generation_ms,
    }


# ============================================================
# Statistics
# ============================================================


def percentile(values, p):
    if not values:
        return None

    values = sorted(values)
    index = (len(values) - 1) * p / 100
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    fraction = index - lower

    return round(
        values[lower] * (1 - fraction) + values[upper] * fraction,
        4,
    )


def summarize_runs(records):
    successful = [record for record in records if record.get("status") == "success"]

    latencies = [record["performance"]["end_to_end_sec"] for record in successful]

    def mean_metric(path):
        values = []
        for record in successful:
            value = record
            for key in path:
                value = value.get(key) if isinstance(value, dict) else None

            if isinstance(value, (int, float)):
                values.append(value)

        return round(statistics.mean(values), 4) if values else None

    names = []
    for record in successful:
        names.extend(
            normalize_name(name)
            for name in record.get("quality", {}).get("names_extracted", [])
            if isinstance(name, str) and name.strip()
        )

    return {
        "attempts": len(records),
        "successful_runs": len(successful),
        "success_rate": round(len(successful) / len(records), 4) if records else 0,
        "latency_mean_sec": (
            round(statistics.mean(latencies), 4) if latencies else None
        ),
        "latency_p50_sec": percentile(latencies, 50),
        "latency_p95_sec": percentile(latencies, 95),
        "latency_p99_sec": percentile(latencies, 99),
        "mean_generation_tokens_per_sec": mean_metric(
            ["performance", "generation_tokens_per_sec"]
        ),
        "valid_json_rate": mean_metric(["quality", "valid_json"]),
        "schema_compliance_rate": mean_metric(["quality", "correct_schema"]),
        "count_match_rate": mean_metric(["quality", "count_match"]),
        "all_unique_rate": mean_metric(["quality", "all_unique"]),
        "length_compliance_rate": mean_metric(["quality", "length_compliance_rate"]),
        "mean_keyword_relevance": mean_metric(["quality", "keyword_relevance"]),
        "distinct_names_across_runs": len(set(names)),
        "cross_run_unique_rate": round(len(set(names)) / len(names), 4) if names else 0,
    }


# ============================================================
# Persistent results
# ============================================================


def save_results(new_record):
    history = []

    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as file:
                loaded = json.load(file)

            if isinstance(loaded, list):
                history = loaded
            else:
                print(
                    f"Warning: {RESULTS_FILE} is not a JSON list; "
                    "starting a new history."
                )
        except (json.JSONDecodeError, OSError) as error:
            print(f"Warning: Could not read previous results: {error}")

    history.append(new_record)

    temporary_file = RESULTS_FILE + ".tmp"

    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=2, ensure_ascii=False)
        file.write("\n")

    os.replace(temporary_file, RESULTS_FILE)


# ============================================================
# One benchmark request
# ============================================================


def run_one(session, strategy, run_index, warmup=False):
    payload = get_payload(strategy)
    started = time.perf_counter()

    record = {
        "version": "v2",
        "strategy_name": STRATEGY.__class__.__name__,
        "timestamp": datetime.now(UTC).isoformat(),
        "model": MODEL_NAME,
        "run_index": run_index,
        "warmup": warmup,
        "temperature": TEMPERATURE,
        "case_id": "developer-tools",
    }

    try:
        response = session.post(
            API_URL,
            json=payload,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        response.raise_for_status()

        elapsed = time.perf_counter() - started
        data = response.json()

        choices = data.get("choices") or []
        if not choices:
            raise ValueError("Response contains no choices")

        message = choices[0].get("message") or {}
        raw_content = message.get("content")

        if not isinstance(raw_content, str):
            raise ValueError("Response message has no string content")

        record.update(
            {
                "status": "success",
                "performance": extract_performance(data, elapsed),
                "quality": evaluate_quality(raw_content, strategy),
                "raw_output": raw_content,
            }
        )

        # Capture server-reported termination reason.
        record["finish_reason"] = choices[0].get("finish_reason")

    except requests.exceptions.Timeout as error:
        record.update(
            {
                "status": "timeout",
                "error": str(error),
                "performance": {
                    "end_to_end_sec": round(time.perf_counter() - started, 4)
                },
            }
        )

    except requests.exceptions.RequestException as error:
        record.update(
            {
                "status": "request_error",
                "error": str(error),
                "performance": {
                    "end_to_end_sec": round(time.perf_counter() - started, 4)
                },
            }
        )

    except (ValueError, KeyError, TypeError) as error:
        record.update(
            {
                "status": "invalid_response",
                "error": str(error),
                "performance": {
                    "end_to_end_sec": round(time.perf_counter() - started, 4)
                },
            }
        )

    return record


# ============================================================
# Main benchmark
# ============================================================


def run_benchmark():
    print(f"Model:       {MODEL_NAME}")
    print(f"Endpoint:    {API_URL}")
    print(f"Trials:      {RUNS}")
    print(f"Warm-ups:    {WARMUP_RUNS}")
    print(f"Name count:  {COUNT}")
    print(f"Max length:  {MAX_LENGTH} characters")
    print("=" * 60)

    records = []

    with requests.Session() as session:
        for index in range(1, WARMUP_RUNS + 1):
            print(f"Warm-up {index}/{WARMUP_RUNS}...", end=" ")

            record = run_one(session, STRATEGY, index, warmup=True)

            if record["status"] == "success":
                print("OK")
            else:
                print(f"FAILED ({record.get('error', record['status'])})")

        for index in range(1, RUNS + 1):
            print(f"Run {index}/{RUNS}...", end=" ")

            record = run_one(session, STRATEGY, index, warmup=False)
            records.append(record)

            if record["status"] == "success":
                performance = record["performance"]
                quality = record["quality"]

                print(
                    f"{performance['end_to_end_sec']:.2f}s | "
                    f"{performance['generation_tokens_per_sec']} gen TPS | "
                    f"JSON={quality['valid_json']} | "
                    f"count={quality['count_match']} | "
                    f"unique={quality['all_unique']}"
                )
            else:
                print(f"FAILED: {record.get('error', record['status'])}")

    summary = summarize_runs(records)

    benchmark_record = {
        "version": "v2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": MODEL_NAME,
        "config": {
            "temperature": TEMPERATURE,
            "runs": RUNS,
            "warmup_runs": WARMUP_RUNS,
            "count": COUNT,
            "max_length": MAX_LENGTH,
            "product_description": PRODUCT_DESCRIPTION,
            "keywords": KEYWORDS,
        },
        "summary": summary,
        "runs": records,
    }

    save_results(benchmark_record)

    print("\n" + "=" * 60)
    print(f"BENCHMARK SUMMARY: {MODEL_NAME}")
    print("=" * 60)
    print(f"Successful runs:      {summary['successful_runs']}/{RUNS}")
    print(f"Success rate:         {summary['success_rate']:.1%}")

    for label, key in [
        ("Mean latency", "latency_mean_sec"),
        ("P50 latency", "latency_p50_sec"),
        ("P95 latency", "latency_p95_sec"),
        ("P99 latency", "latency_p99_sec"),
        ("Mean generation TPS", "mean_generation_tokens_per_sec"),
    ]:
        print(f"{label:22} {summary[key]}")

    print("\nQuality rates:")
    for label, key in [
        ("Valid JSON", "valid_json_rate"),
        ("Schema compliant", "schema_compliance_rate"),
        ("Correct count", "count_match_rate"),
        ("All names unique", "all_unique_rate"),
        ("Length compliant", "length_compliance_rate"),
        ("Keyword relevance", "mean_keyword_relevance"),
    ]:
        value = summary[key]
        print(f"{label:22} {value:.1%}" if value is not None else f"{label:22} N/A")

    print(f"\nDistinct names across runs: {summary['distinct_names_across_runs']}")
    print(f"Cross-run unique rate:      {summary['cross_run_unique_rate']:.1%}")

    successful = summary["successful_runs"]
    if successful == 0:
        print("\nNo successful runs. Check llama-server and its logs.")
    else:
        print("\nExample output from the last successful run:")
        for record in reversed(records):
            if record["status"] == "success":
                print(
                    json.dumps(
                        record["quality"]["names_extracted"],
                        indent=2,
                        ensure_ascii=False,
                    )
                )
                break

    print(f"\nResults appended to {RESULTS_FILE}")


if __name__ == "__main__":
    run_benchmark()
