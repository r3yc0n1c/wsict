import json
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

import requests
from keywords import extract_keywords
from templates_v2 import *

OUTPUT_DIR = Path("product_names")
OUTPUT_DIR.mkdir(exist_ok=True)

LLM_API = "http://127.0.0.1:8080/v1/chat/completions"
HEADERS = {"Content-Type": "application/json"}

MODEL = "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M"
TEMPERATURE = 0.7
STRATEGY_NAMES = [x.STRATEGY_NAME for x in STRATEGIES] + ["all"]
STRATEGIES_MENU = (
    "\n".join([f"[{i}] " + s for i, s in enumerate(STRATEGY_NAMES)]) + "\n[?]> "
)


def get_payload(count, product_description, keywords, strategy):
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
        "model": MODEL,
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
                    count, product_description, keywords
                ),
            },
        ],
        "stream": False,
    }

    return payload


def get_names(count, product_description, keywords, strategy):

    try:
        data = get_payload(count, product_description, keywords, strategy)
        # print(data)
        res = requests.post(LLM_API, json=data, headers=HEADERS)
        res.raise_for_status()

        result = res.json()
        # print(result)

        names = result["choices"][0]["message"]["content"]
        # print(names)
        return json.loads(names)["product_names"]

    except requests.exceptions.RequestException as e:
        print(f"HTTP request failed: {e}")
        if getattr(e, "response", None) is not None:
            print(e.response.text)
    except (ValueError, KeyError, IndexError) as e:
        print(f"Unexpected response format: {e}")
        if "res" in locals():
            print(res.text)


if __name__ == "__main__":
    results = {
        "metadata": {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "endpoint": LLM_API,
            "model": MODEL,
            "temperature": TEMPERATURE,
        },
        "product_data": {}
    }

    try:
        description = input("Enter your product description: ")
        count = int(input("Total names: "))
        i = int(input(STRATEGIES_MENU))

        results["product_data"]["description"] = description
        results["product_data"]["count"] = count
        results["product_data"]["strategies"] = {}

        keywords = extract_keywords(description)

        if len(keywords) <= 0:
            sys.exit("Fix keyword gen")

        print("KEYWORDS:")
        print(json.dumps(keywords, indent=2, ensure_ascii=False))

        results["product_data"]["keywords"] = keywords

        # strategy = 'all'
        if i == len(STRATEGY_NAMES) - 1:
            for STRATEGY in STRATEGIES:
                s = STRATEGY()
                names = get_names(count, description, keywords, s)
                print("=" * 16)
                print(s.STRATEGY_NAME)
                print("=" * 16)
                print(names)
                results["product_data"]["strategies"][s.STRATEGY_NAME] = names
        else:
            s = STRATEGIES[i]()

            print("=" * 16)
            print(s.STRATEGY_NAME)
            print("=" * 16)

            names = get_names(count, description, keywords, s)
            print(names)
            results["product_data"]["strategies"][s.STRATEGY_NAME] = names

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = OUTPUT_DIR / f"product_{timestamp}.json"
        json_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    except requests.RequestException as exc:
        print(f"LLM API request failed: {exc}")
        traceback.print_exc()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        print(f"Keyword extraction failed: {exc}")
        traceback.print_exc()
