#!/usr/bin/env python3

import argparse
import json
import math
import re
import statistics
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests
from templates_v2 import STOPWORDS, BalancedStrategy

"""
# ----- Supported Models -----
1. Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M
2. bartowski/Llama-3.2-1B-Instruct-GGUF:Q4_K_M
3. HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF:Q4_K_M

# ----- Usage -----
python3 benchmark_v3.py \
  --models "Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M" \
  --runs 10 \
  --warmups 1
"""

# ── Configuration ────────────────────────────────────────────────

BASE_URL = "http://127.0.0.1:8080/v1"
CHAT_URL = f"{BASE_URL}/chat/completions"

# Replace these with model IDs actually served by your endpoint.
# A standard llama-server serves one model at a time unless configured
# with a router or another multi-model setup.
MODELS = [
    "Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M",
    # "bartowski/Llama-3.2-1B-Instruct-GGUF:Q4_K_M",
]

PRODUCT_DESCRIPTION = (
    "An AI-powered tool that generates creative, memorable names "
    "for software products and startups."
)

KEYWORDS = "brand, naming, creativity, identity, software, startup"

COUNT = 10
RUNS = 10
WARMUP_RUNS = 1
TEMPERATURE = 0.7
REQUEST_TIMEOUT = 180

# The strategy's prompt uses fewer than MAX_LENGTH characters.
MAX_LENGTH = BalancedStrategy.MAX_LENGTH

OUTPUT_DIR = Path("benchmark_results")
OUTPUT_DIR.mkdir(exist_ok=True)


# ── Text and response helpers ────────────────────────────────────


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def parse_response(content):
    """Parse the expected JSON object, tolerating surrounding fences."""
    content = content.strip()

    # Handle models that wrap JSON in Markdown fences.
    content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.I)
    content = re.sub(r"\s*```$", "", content)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Recover a JSON object/array embedded in extra text if possible.
        match = re.search(r"\{.*\}|\[.*\]", content, flags=re.S)
        if not match:
            raise
        data = json.loads(match.group(0))

    schema_ok = (
        isinstance(data, dict)
        and isinstance(data.get("product_names"), list)
        and all(isinstance(name, str) for name in data["product_names"])
    )

    if schema_ok:
        names = data["product_names"]
    elif isinstance(data, list) and all(isinstance(n, str) for n in data):
        # Parse successfully, but flag the wrong schema.
        names = data
    else:
        names = []

    return data, names, schema_ok


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * pct / 100
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def safe_mean(values):
    return statistics.mean(values) if values else None


def safe_rate(numerator, denominator):
    return numerator / denominator if denominator else None


def round_or_none(value, digits=3):
    return round(value, digits) if value is not None else None


# ── Quality metrics ─────────────────────────────────────────────


def score_names(names, keywords, description, max_length, requested_count):
    valid_names = [n.strip() for n in names if isinstance(n, str) and n.strip()]

    normalized = [n.casefold() for n in valid_names]
    unique_count = len(set(normalized))

    lengths = [len(n) for n in valid_names]
    length_ok = [bool(n) and len(n) < max_length for n in valid_names]

    # Treat words from the product description and supplied keywords
    # as relevance signals. This is a rough lexical metric only.
    keyword_tokens = {
        token
        for token in tokenize(keywords + " " + description)
        if len(token) > 2 and token not in STOPWORDS
    }

    def name_tokens(name):
        return {token for token in tokenize(name) if len(token) > 1}

    relevant = []
    for name in valid_names:
        tokens = name_tokens(name)
        relevant.append(bool(tokens & keyword_tokens))

    # Pairwise lexical diversity: 1 - Jaccard similarity.
    # Higher means the names share fewer tokens.
    pairwise_diversity = []
    for i in range(len(valid_names)):
        for j in range(i + 1, len(valid_names)):
            a = name_tokens(valid_names[i])
            b = name_tokens(valid_names[j])
            union = a | b
            similarity = len(a & b) / len(union) if union else 1.0
            pairwise_diversity.append(1.0 - similarity)

    # Simple pronounceability proxy, not a phonetic or human evaluation.
    def pronounceable(name):
        letters = re.sub(r"[^a-z]", "", name.lower())
        if not letters:
            return False

        # Penalize long consonant runs and names without vowels.
        has_vowel = bool(re.search(r"[aeiouy]", letters))
        long_consonant_run = bool(re.search(r"[^aeiouy]{4,}", letters))
        return has_vowel and not long_consonant_run

    pronounceability = [pronounceable(n) for n in valid_names]

    # Measure repetition of the same whole name across generated batches
    # separately in the model-level aggregation.
    return {
        "requested_count": requested_count,
        "returned_count": len(names),
        "nonempty_count": len(valid_names),
        "count_correct": len(names) == requested_count,
        "unique_names": unique_count,
        "unique_rate": safe_rate(unique_count, len(valid_names)),
        "all_names_unique": unique_count == len(valid_names),
        "length_compliant_count": sum(length_ok),
        "length_compliance_rate": safe_rate(sum(length_ok), len(valid_names)),
        "mean_name_length": safe_mean(lengths),
        "keyword_relevant_count": sum(relevant),
        "keyword_relevance_rate": safe_rate(sum(relevant), len(valid_names)),
        "pronounceable_count": sum(pronounceability),
        "pronounceability_rate": safe_rate(sum(pronounceability), len(valid_names)),
        "pairwise_diversity": safe_mean(pairwise_diversity),
        "names": valid_names,
    }


# ── One request ──────────────────────────────────────────────────


def call_model(session, model, strategy):
    user_prompt = strategy.get_user_prompt(
        count=COUNT,
        product_description=PRODUCT_DESCRIPTION,
        keywords=KEYWORDS,
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": strategy.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": TEMPERATURE,
        "stream": False,
    }

    start = time.perf_counter()
    try:
        response = session.post(
            CHAT_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        elapsed = time.perf_counter() - start
        response.raise_for_status()
        body = response.json()

        content = body["choices"][0]["message"]["content"]
        finish_reason = body["choices"][0].get("finish_reason")
        usage = body.get("usage", {})

        parse_ok = False
        schema_ok = False
        names = []
        parse_error = None

        try:
            _, names, schema_ok = parse_response(content)
            parse_ok = True
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            parse_error = str(exc)

        quality = score_names(
            names=names,
            keywords=KEYWORDS,
            description=PRODUCT_DESCRIPTION,
            max_length=MAX_LENGTH,
            requested_count=COUNT,
        )

        completion_tokens = usage.get("completion_tokens")
        prompt_tokens = usage.get("prompt_tokens")
        total_tokens = usage.get("total_tokens")

        # Some compatible servers omit usage. In that case, report TPS
        # as unavailable instead of pretending character count is tokens.
        generation_seconds = elapsed
        tps = (
            completion_tokens / generation_seconds
            if completion_tokens is not None and generation_seconds > 0
            else None
        )

        return {
            "success": True,
            "model": model,
            "latency_seconds": elapsed,
            "http_status": response.status_code,
            "parse_ok": parse_ok,
            "schema_ok": schema_ok,
            "finish_reason": finish_reason,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "generation_tokens_per_second": tps,
            "parse_error": parse_error,
            "raw_response": content,
            **quality,
        }

    except Exception as exc:
        return {
            "success": False,
            "model": model,
            "latency_seconds": time.perf_counter() - start,
            "error": f"{type(exc).__name__}: {exc}",
            "parse_ok": False,
            "schema_ok": False,
            "count_correct": False,
            "all_names_unique": False,
            "names": [],
        }


# ── Model-level aggregation ──────────────────────────────────────


def summarize_model(model, records):
    successful = [r for r in records if r["success"]]
    latencies = [r["latency_seconds"] for r in successful]
    parseable = [r for r in successful if r["parse_ok"]]
    schema_valid = [r for r in successful if r["schema_ok"]]

    def values(key, rows=successful):
        return [
            r[key]
            for r in rows
            if isinstance(r.get(key), (int, float)) and not isinstance(r.get(key), bool)
        ]

    all_names = [n.casefold() for r in successful for n in r.get("names", [])]
    total_names = len(all_names)
    distinct_names = len(set(all_names))

    summary = {
        "model": model,
        "runs": len(records),
        "successful_requests": len(successful),
        "request_success_rate": safe_rate(len(successful), len(records)),
        "valid_json_rate": safe_rate(len(parseable), len(successful)),
        "schema_compliance_rate": safe_rate(len(schema_valid), len(successful)),
        "correct_count_rate": safe_rate(
            sum(bool(r.get("count_correct")) for r in successful),
            len(successful),
        ),
        "all_names_unique_batch_rate": safe_rate(
            sum(bool(r.get("all_names_unique")) for r in successful),
            len(successful),
        ),
        "unique_name_rate_across_all_runs": safe_rate(distinct_names, total_names),
        "length_compliance_rate": safe_mean(values("length_compliance_rate")),
        "keyword_relevance_rate": safe_mean(values("keyword_relevance_rate")),
        "pronounceability_rate": safe_mean(values("pronounceability_rate")),
        "pairwise_diversity": safe_mean(values("pairwise_diversity")),
        "mean_latency_seconds": safe_mean(latencies),
        "p50_latency_seconds": percentile(latencies, 50),
        "p95_latency_seconds": percentile(latencies, 95),
        "p99_latency_seconds": percentile(latencies, 99),
        "mean_generation_tokens_per_second": safe_mean(
            values("generation_tokens_per_second")
        ),
        "mean_completion_tokens": safe_mean(values("completion_tokens")),
        "mean_prompt_tokens": safe_mean(values("prompt_tokens")),
    }

    # A transparent composite score, excluding speed/reliability.
    # Keep component metrics in the report; don't rely on this alone.
    quality_components = [
        summary["correct_count_rate"],
        summary["all_names_unique_batch_rate"],
        summary["length_compliance_rate"],
        summary["pronounceability_rate"],
        summary["pairwise_diversity"],
    ]

    available = [x for x in quality_components if x is not None]
    summary["heuristic_quality_score_0_to_100"] = (
        round(100 * statistics.mean(available), 2) if available else None
    )

    return summary


# ── Main benchmark ───────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark local LLMs for product naming."
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=MODELS,
        help="Model IDs served by the OpenAI-compatible endpoint.",
    )
    parser.add_argument("--runs", type=int, default=RUNS)
    parser.add_argument("--warmups", type=int, default=WARMUP_RUNS)
    args = parser.parse_args()

    if not args.models:
        parser.error("Provide at least one model with --models.")

    strategy = BalancedStrategy()
    session = requests.Session()

    # Check endpoint reachability before spending time on the benchmark.
    try:
        r = session.get(f"{BASE_URL}/models", timeout=5)
        r.raise_for_status()
        print("Endpoint reachable:", f"{BASE_URL}/models")
        try:
            print("Available models:")
            for item in r.json().get("data", []):
                print("  -", item.get("id", item))
        except (ValueError, AttributeError):
            pass
    except requests.RequestException as exc:
        raise SystemExit(f"Cannot reach {BASE_URL}. Start your server first.\n{exc}")

    results = {
        "metadata": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "endpoint": BASE_URL,
            "strategy": type(strategy).__name__,
            "system_prompt": strategy.SYSTEM_PROMPT,
            "user_prompt_template": strategy.USER_PROMPT,
            "product_description": PRODUCT_DESCRIPTION,
            "keywords": KEYWORDS,
            "count": COUNT,
            "max_name_length_exclusive": MAX_LENGTH,
            "temperature": TEMPERATURE,
            "runs_per_model": args.runs,
            "warmup_runs": args.warmups,
        },
        "models": {},
    }

    summaries = []

    for model in args.models:
        print(f"\n{'=' * 72}\nModel: {model}")
        records = []

        for i in range(args.warmups):
            print(f"Warmup {i + 1}/{args.warmups}...", end=" ", flush=True)
            warmup = call_model(session, model, strategy)
            print("OK" if warmup["success"] else warmup.get("error", "FAILED"))

        for i in range(args.runs):
            print(f"Run {i + 1}/{args.runs}...", end=" ", flush=True)
            result = call_model(session, model, strategy)
            records.append(result)

            if result["success"]:
                print(
                    f"{result['latency_seconds']:.2f}s | "
                    f"JSON={result['parse_ok']} | "
                    f"schema={result['schema_ok']} | "
                    f"count={result.get('returned_count', 0)}/{COUNT}"
                )
            else:
                print("FAILED:", result.get("error"))

        summary = summarize_model(model, records)
        summaries.append(summary)
        results["models"][model] = {
            "summary": summary,
            "runs": records,
        }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = OUTPUT_DIR / f"benchmark_{timestamp}.json"
    json_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Compact terminal comparison.
    print("\n\nFINAL COMPARISON")
    columns = [
        ("model", "Model"),
        ("request_success_rate", "Success"),
        ("schema_compliance_rate", "Schema"),
        ("correct_count_rate", "Count"),
        ("length_compliance_rate", "Length"),
        ("keyword_relevance_rate", "Keyword"),
        ("mean_latency_seconds", "Mean s"),
        ("p95_latency_seconds", "P95 s"),
        ("mean_generation_tokens_per_second", "Tok/s"),
        ("heuristic_quality_score_0_to_100", "Quality"),
    ]

    def fmt(key, value):
        if value is None:
            return "N/A"
        if key == "model":
            return str(value)
        if key.endswith("_rate"):
            return f"{value * 100:.1f}%"
        if isinstance(value, (int, float)):
            return f"{value:.2f}"
        return str(value)

    widths = {
        key: max(len(label), *(len(fmt(key, row.get(key))) for row in summaries))
        for key, label in columns
    }

    print(" | ".join(label.ljust(widths[key]) for key, label in columns))
    print("-+-".join("-" * widths[key] for key, _ in columns))

    for row in summaries:
        print(
            " | ".join(fmt(key, row.get(key)).ljust(widths[key]) for key, _ in columns)
        )

    print(f"\nFull results saved to: {json_path}")


if __name__ == "__main__":
    main()
