import json
import os
import traceback

import requests
from dotenv import load_env_file

load_env_file()

LLM_API = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = os.getenv("MODEL")
API_KEY = os.getenv("API_KEY")
HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
TEMPERATURE = 0.7

SYSTEM_PROMPT = """
You are a product naming research assistant.

Extract 8-15 concise, meaningful keywords from the provided
software product description to help generate distinctive names.

Rules:
- Identify the core purpose, audience, features, and benefits.
- Include functional, conceptual, and evocative keywords.
- Prefer specific terms over generic words like app, software,
  platform, and tool.
- Use lowercase strings.
- Remove duplicates, filler words, and irrelevant concepts.
- Do not invent features or claims.
- Return ONLY a valid JSON array of strings.
- Do not include markdown or explanations.
""".strip()

schema = {
    "name": "keywords",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "A list of unique 8-15 keywords related to the product description.",
            }
        },
        "required": ["keywords"],
        "additionalProperties": False,
    },
}


def extract_keywords(product_description: str) -> list[str]:
    if not product_description.strip():
        raise ValueError("Product description cannot be empty.")

    payload = {
        "model": MODEL,
        "temperature": TEMPERATURE,
        "response_format": {"type": "json_schema", "json_schema": schema},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Extract 8-15 keywords from this product description:\n\n"
                    f"{product_description.strip()}"
                ),
            },
        ],
    }

    response = requests.post(
        LLM_API,
        json=payload,
        headers=HEADERS,
        timeout=(5, 90),
    )
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    # print("Raw LLM response:", repr(content))
    keywords = json.loads(content)["keywords"]

    if not isinstance(keywords, list):
        raise ValueError("Model response must be a JSON array.")

    # Validate, normalize, and deduplicate the output.
    cleaned = []
    seen = set()

    for item in keywords:
        if not isinstance(item, str):
            continue

        keyword = item.strip().lower()

        if keyword and keyword not in seen:
            seen.add(keyword)
            cleaned.append(keyword)

    # if not 8 <= len(cleaned) <= 15:
    #     raise ValueError(f"Expected 8-15 keywords, received {len(cleaned)}: {cleaned}")

    return cleaned


if __name__ == "__main__":
    description = input("Enter your product description: ")

    try:
        keywords = extract_keywords(description)
        print(json.dumps(keywords, indent=2, ensure_ascii=False))
    except requests.RequestException as exc:
        print(f"LLM API request failed: {exc}")
        traceback.print_exc()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        print(f"Keyword extraction failed: {exc}")
        traceback.print_exc()
