import glob
import json
import sys
from datetime import datetime
from pathlib import Path

import requests

INPUT_DIR = Path("product_names")
LLM_API = "http://127.0.0.1:8080/v1/chat/completions"
HEADERS = {"Content-Type": "application/json"}
MODEL = "unsloth/Qwen3.5-4B-GGUF:Q4_K_M"
TEMPERATURE = 0.7

SYSTEM_PROMPT = """Act as an expert brand strategist, linguist, and software naming consultant.
You will evaluate a list of potential names for a new software product.

The Rubric (Score each name mentally on these criteria):
1. Brevity & Visual Impact: Is it short (under 10 characters)? Does it look visually balanced?
2. Pronounceability (The Radio Test): Is it easy to spell if heard spoken out loud?
3. Memorability & "Stickiness": Does it stand out from generic tech names?
4. Evocative Power: Does it subtly hint at the product's value without being boringly literal?
5. Global Safety: Does it avoid unintended awkward linguistic twists?

Output Format Requirements:
You must return a strict JSON object categorizing the names into four tiers.
- tier_1: The top 5 absolute best names, including a 1-sentence reason and a score out of 10.
- tier_2: The next best names (strong contenders).
- tier_3: Functional but generic names that lack magic.
- tier_4: The rejected names, along with the most common fatal flaw among them (e.g., "Too literal")."""


def get_latest_generation():
    files = glob.glob(f"{INPUT_DIR}/product_*.json")
    if not files:
        sys.exit("No product JSON files found in product_names/ directory.")
    latest_file = max(files, key=lambda x: Path(x).stat().st_mtime)
    return latest_file

def sort_names(ranking_data):
    ranking_data["tier_1"].sort(key=lambda x: x["name"].lower())
    ranking_data["tier_2"].sort(key=str.lower)
    ranking_data["tier_3"].sort(key=str.lower)
    ranking_data["tier_4"]["names"].sort(key=str.lower)

def rank_names(description, target_audience, names, source_file_path):
    # Define the backup cache file path
    cache_file = source_file_path.with_name(f"{source_file_path.stem}_raw.json")

    # FAILSAFE STEP 1: Check for existing cache
    if cache_file.exists():
        print(f"\n[*] Found cached LLM response: {cache_file.name}")
        print(
            "[*] Skipping API call. (Delete this file if you want to force a new LLM generation)"
        )
        raw_json = cache_file.read_text(encoding="utf-8")
    else:
        schema = {
            "name": "name_rankings",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "tier_1": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "reason": {"type": "string"},
                                "score": {"type": "integer"},
                            },
                            "required": ["name", "reason", "score"],
                            "additionalProperties": False,
                        },
                    },
                    "tier_2": {"type": "array", "items": {"type": "string"}},
                    "tier_3": {"type": "array", "items": {"type": "string"}},
                    "tier_4": {
                        "type": "object",
                        "properties": {
                            "names": {"type": "array", "items": {"type": "string"}},
                            "fatal_flaw": {"type": "string"},
                        },
                        "required": ["names", "fatal_flaw"],
                        "additionalProperties": False,
                    },
                },
                "required": ["tier_1", "tier_2", "tier_3", "tier_4"],
                "additionalProperties": False,
            },
        }

        user_content = f"""Product Description: {description}
Target Audience: {target_audience}
Vibe/Tone: Professional, modern, memorable, and clever.

Here is the list of {len(names)} names to evaluate:
{", ".join(names)}
"""

        payload = {
            "model": MODEL,
            "temperature": TEMPERATURE,
            "response_format": {"type": "json_schema", "json_schema": schema},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "stream": False,
        }

        try:
            print(f"Sending {len(names)} names to LLM for ranking. Please wait...\n")
            res = requests.post(LLM_API, json=payload, headers=HEADERS)
            res.raise_for_status()

            result = res.json()
            raw_json = result["choices"][0]["message"]["content"]
            print(raw_json)

            # FAILSAFE STEP 2: Instantly write raw output to disk before parsing
            cache_file.write_text(raw_json, encoding="utf-8")
            print(f"[+] Raw LLM response backed up to: {cache_file}")

        except requests.exceptions.RequestException as e:
            print(f"HTTP request failed: {e}")
            if getattr(e, "response", None) is not None:
                print(e.response.text)
            sys.exit(1)

    # FAILSAFE STEP 3: Attempt to parse, with graceful failure instructions
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"\n[!] Failed to parse LLM response as JSON: {e}")
        print("[!] Don't worry, your LLM call wasn't wasted!")
        print(f"[!] Open this file: {cache_file}")
        print(
            "[!] Fix the syntax error (e.g. add the missing bracket/quote at the end), save it, and re-run this script."
        )
        sys.exit(1)


if __name__ == "__main__":
    INPUT_DIR.mkdir(exist_ok=True)

    latest_file = get_latest_generation()
    latest_file_path = Path(latest_file)
    print(f"Loading names from: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            sys.exit("The input JSON file is already corrupted or invalid.")

    description = data.get("product_data", {}).get("description", "A software product.")

    all_names = set()
    for names_list in data.get("product_data", {}).get("strategies", {}).values():
        all_names.update(names_list)

    all_names = list(all_names)

    if not all_names:
        sys.exit("No names found in the JSON file.")

    target_audience = input(
        "Enter the target audience (e.g., developers, consumers, enterprise HR): "
    )
    if not target_audience.strip():
        target_audience = "General software users"

    # Pass the source file path to our ranking function so it knows where to save the backup
    ranking_data = rank_names(description, target_audience, all_names, latest_file_path)
    sort_names(ranking_data)

    if "product_data" not in data:
        data["product_data"] = {}

    data["product_data"]["rankings"] = ranking_data

    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("=" * 40)
    print("RANKING COMPLETE")
    print("=" * 40)
    print(f"Successfully added JSON rankings directly to: {latest_file}")

    # FAILSAFE STEP 4: Clean up the cache only if everything fully succeeded
    cache_to_delete = latest_file_path.with_name(f"{latest_file_path.stem}_raw.json")
    if cache_to_delete.exists():
        cache_to_delete.unlink()
        print(f"Cleaned up temporary cache file: {cache_to_delete.name}")
