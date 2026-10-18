import json
import os
import re
import sys
import time

import requests
from templates import ForgeMintStrategy

if len(sys.argv) <= 1:
    sys.exit("Usage: python3 benchmark.py <model-name>")

# Allow passing the model name via command line, e.g., `python benchmark.py qwen2.5`
MODEL_NAME = sys.argv[1]
TEMPERATURE = 0.7

API_URL = "http://127.0.0.1:8080/v1/chat/completions"
RESULTS_FILE = "benchmark_results.json"

# Product Specs
COUNT = 10
PRODUCT_DESCRIPTION = "An AI-powered name generator for software products that checks domain and GitHub availability."
KEYWORDS = "forge, mint, craft, syntax, token, nym, moniker, alias"


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
                    "description": "A list of unique software product names under 12 characters.",
                }
            },
            "required": ["product_names"],
            "additionalProperties": False,
        },
    }

    payload = {
        "model": MODEL_NAME,
        "temperature": TEMPERATURE,
        "response_format": {"type": "json_schema", "json_schema": schema},
        "messages": [
            {
                "role": "system",
                "content": strategy.SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": strategy.get_user_prompt(
                    COUNT, PRODUCT_DESCRIPTION, KEYWORDS
                ),
            },
        ],
    }

    return payload


def normalize_name(name):
    return re.sub(r"\s+", "", name).casefold()


def evaluate_quality(raw_content, strategy):
    max_length = strategy.MAX_LENGTH

    quality = {
        "valid_json": False,
        "names_extracted": [],
        "count_match": False,
        "all_under_max_length": False,
        "all_unique": False,
        "unique_rate": 0.0,
        "valid_name_rate": 0.0,
        "length_compliance_rate": 0.0,
        "keyword_relevance": 0.0,
        "average_length": 0.0,
    }

    try:
        parsed = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError):
        return quality

    if not isinstance(parsed, dict):
        return quality

    names = parsed.get("product_names")
    if not isinstance(names, list):
        return quality

    quality["valid_json"] = True
    quality["names_extracted"] = names
    quality["count_match"] = len(names) == COUNT

    if not names:
        return quality

    valid_names = [
        name for name in names if isinstance(name, str) and bool(name.strip())
    ]

    quality["valid_name_rate"] = round(len(valid_names) / len(names), 4)

    normalized = [normalize_name(n) for n in valid_names]
    quality["unique_rate"] = round(len(set(normalized)) / len(names), 4)
    quality["all_unique"] = len(valid_names) == len(names) and len(
        set(normalized)
    ) == len(names)

    compliant = [name for name in valid_names if len(name) < max_length]

    quality["length_compliance_rate"] = round(len(compliant) / len(names), 4)
    quality["all_under_max_length"] = len(valid_names) == len(names) and len(
        compliant
    ) == len(names)

    quality["average_length"] = (
        round(sum(len(n) for n in valid_names) / len(valid_names), 2)
        if valid_names
        else 0
    )

    keywords = [k.casefold() for k in KEYWORDS.split(",") if k.strip()]

    if valid_names and keywords:
        relevant = sum(
            any(k in name.casefold() for k in keywords) for name in valid_names
        )
        quality["keyword_relevance"] = round(relevant / len(valid_names), 4)

    return quality


def extract_performance(data, elapsed_sec):
    usage = data.get("usage", {})
    timings = data.get("timings", {})

    completion_tokens = usage.get("completion_tokens", 0)
    prompt_tokens = usage.get("prompt_tokens", 0)

    # Prefer server-side generation timing when available.
    generation_ms = timings.get("predicted_ms")
    generation_sec = (
        generation_ms / 1000
        if isinstance(generation_ms, (int, float)) and generation_ms > 0
        else None
    )

    generation_tps = timings.get("predicted_per_second")
    if generation_tps is None and generation_sec:
        generation_tps = completion_tokens / generation_sec

    return {
        "end_to_end_sec": round(elapsed_sec, 4),
        "generation_sec": (
            round(generation_sec, 4) if generation_sec is not None else None
        ),
        "completion_tokens": completion_tokens,
        "prompt_tokens": prompt_tokens,
        "total_tokens": usage.get("total_tokens", prompt_tokens + completion_tokens),
        "end_to_end_tokens_per_sec": round(completion_tokens / elapsed_sec, 2)
        if elapsed_sec > 0
        else 0,
        "generation_tokens_per_sec": (
            round(generation_tps, 2)
            if isinstance(generation_tps, (int, float))
            else None
        ),
        "prompt_tokens_per_sec": timings.get("prompt_per_second"),
        "prompt_processing_ms": timings.get("prompt_ms"),
        "server_generation_ms": generation_ms,
    }


def run_benchmark():
    print(f"Testing {MODEL_NAME} on {API_URL}...")
    start_time = time.perf_counter()

    strategy = ForgeMintStrategy()
    payload = get_payload(strategy)

    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()

        end_time = time.perf_counter()
        data = response.json()

        # Extract base metrics
        generation_time = end_time - start_time
        raw_content = data["choices"][0]["message"]["content"]
        tokens_generated = data["usage"]["completion_tokens"]
        tps = tokens_generated / generation_time if generation_time > 0 else 0

        # Evaluattion metrices
        elapsed_sec = end_time - start_time
        performance = extract_performance(data, elapsed_sec)
        quality_metrics = evaluate_quality(raw_content, strategy)

        # Compile final record
        run_record = {
            "version": "v1",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": MODEL_NAME,
            "performance": performance,
            "quality": quality_metrics,
            "raw_output": raw_content,
        }

        # Save to JSON
        save_results(run_record)

        # Console Output
        print("\n" + "=" * 40)
        print(f"RESULTS FOR {MODEL_NAME.upper()}")
        print("=" * 40)
        print(f"Names: {quality_metrics['names_extracted']}")
        print(f"Speed: {tps:.2f} TPS")
        print("Quality Constraints Met:")
        print(f" - Valid JSON Array: {quality_metrics['valid_json']}")
        print(
            f" - Length <= {strategy.MAX_LENGTH} chars: {quality_metrics['all_under_max_length']}"
        )
        print(
            f" - Exactly {COUNT} unique names: {quality_metrics['count_match'] and quality_metrics['all_unique']}"
        )

    except requests.exceptions.ConnectionError:
        print("\nError: Connection refused. Is llama-server running on port 8080?")
    except Exception as e:
        print(f"\nAn error occurred: {e}")


def save_results(new_record):
    history = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                pass

    history.append(new_record)

    with open(RESULTS_FILE, "w") as f:
        json.dump(history, f, indent=4)
    print(f"\n[+] Results saved to {RESULTS_FILE}")


if __name__ == "__main__":
    run_benchmark()
