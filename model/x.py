import json
import requests as req
from templates import *

LLM_API = "http://127.0.0.1:8080/v1/chat/completions"

# MODEL = "unsloth/Llama-3.2-3B-Instruct-GGUF:UD-Q4_K_XL"
# MODEL = "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M"
MODEL = "bartowski/Llama-3.2-1B-Instruct-GGUF:Q4_K_M"

TEMPERATURE = 0.7
HEADERS = {"Content-Type": "application/json"}


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
    }

    return payload


def get_names(count, product_description, keywords, strategy):

    try:
        data = get_payload(count, product_description, keywords, strategy)
        # print(data)
        res = req.post(LLM_API, json=data, headers=HEADERS)
        res.raise_for_status()

        result = res.json()
        # print(result)

        names = result["choices"][0]["message"]["content"]
        # print(names)
        return json.loads(names)["product_names"]

    except req.exceptions.RequestException as e:
        print(f"HTTP request failed: {e}")
        if getattr(e, "response", None) is not None:
            print(e.response.text)
    except (ValueError, KeyError, IndexError) as e:
        print(f"Unexpected response format: {e}")
        if "res" in locals():
            print(res.text)


def test_single_strategy(count, product_description, keywords):
    strategy = ForgeMintStrategy()
    names = get_names(count, product_description, keywords, strategy)
    print(names)


def test_all_strategy(count, product_description, keywords):
    strategy_list = [
        ForgeMintStrategy(),
        AbstractEvocativeStrategy(),
        DeveloperSyntaxStrategy(),
        LinguisticTwistStrategy(),
    ]

    for strategy in strategy_list:
        names = get_names(count, product_description, keywords, strategy)
        print("=" * 16)
        print(strategy.__class__.__name__)
        print("=" * 16)
        # print("-" * 32)
        print(names)


if __name__ == "__main__":
    count = 10
    product_description = "An AI-powered name generator for software products that checks domain and GitHub availability."
    keywords = "forge, mint, craft, syntax, token, nym, moniker, alias"

    # test_single_strategy(count, product_description, keywords)
    test_all_strategy(count, product_description, keywords)
