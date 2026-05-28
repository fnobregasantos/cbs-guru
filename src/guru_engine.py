"""CBS Guru question-answering engine for the prototype."""

from __future__ import annotations

import argparse
import csv
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

try:
    from prompts import CBS_GURU_SYSTEM_PROMPT
except ModuleNotFoundError:
    from src.prompts import CBS_GURU_SYSTEM_PROMPT


CATALOG_PATH = Path("data/processed/variables_catalog.csv")


def ask_cbs_guru(question: str) -> str:
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    vector_store_id = os.environ.get("OPENAI_VECTOR_STORE_ID")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    if not api_key:
        return (
            "OPENAI_API_KEY is missing. Create a `.env` file from `.env.example` "
            "and add your API key."
        )
    if not vector_store_id:
        return (
            "OPENAI_VECTOR_STORE_ID is missing. Upload the PDFs first:\n\n"
            "```bash\npython src/upload_openai_vector_store.py\n```\n\n"
            "Then copy the printed `OPENAI_VECTOR_STORE_ID=...` value into `.env`."
        )

    catalog_context = load_catalog_context(question)
    user_prompt = build_user_prompt(question, catalog_context)

    payload = {
        "model": model,
        "instructions": CBS_GURU_SYSTEM_PROMPT,
        "input": user_prompt,
        "tools": [
            {
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": 20,
            }
        ],
        "include": ["file_search_call.results"],
        "temperature": 0.2,
    }

    try:
        response_data = post_response(api_key, payload)
        answer = extract_response_text(response_data)
    except requests.RequestException as exc:
        return f"OpenAI request failed: {exc}"
    except Exception as exc:
        return f"CBS Guru could not produce an answer: {exc}"

    return answer or "CBS Guru did not return text. Try a narrower question."


def build_user_prompt(question: str, catalog_context: str) -> str:
    return f"""
Question:
{question}

Use the uploaded CBS documentation through file_search. If catalog context is provided below, use it as additional candidate-variable context, but still avoid inventing sources.

Catalog context:
{catalog_context or "No local variables_catalog.csv context available."}

Answer in exactly this structure:

## Short answer

## Recommended CBS variables / candidate concepts

For each variable or candidate:
- Dutch variable name
- English meaning
- Why relevant
- Source PDF
- Evidence / excerpt if available
- Confidence: high / medium / low

## How to use in a research design

## Limitations and things to verify

## Source-check table

The source-check table should have columns:
variable_or_concept | source_pdf | dataset_name_if_known | evidence_strength | notes
"""


def post_response(api_key: str, payload: dict) -> dict:
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    if response.status_code == 400 and "temperature" in payload:
        payload = dict(payload)
        payload.pop("temperature", None)
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=180,
        )
    response.raise_for_status()
    return response.json()


def extract_response_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()

    parts = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if isinstance(content.get("text"), str):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def load_catalog_context(question: str, max_rows: int = 40) -> str:
    if not CATALOG_PATH.exists():
        return ""

    rows = []
    try:
        with CATALOG_PATH.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
    except OSError:
        return ""

    if not rows:
        return ""

    query_terms = tokenize(question)
    scored_rows = sorted(
        rows,
        key=lambda row: score_catalog_row(row, query_terms),
        reverse=True,
    )
    selected = [row for row in scored_rows if score_catalog_row(row, query_terms) > 0]
    if not selected:
        selected = scored_rows[: min(20, len(scored_rows))]
    selected = selected[:max_rows]

    lines = []
    for row in selected:
        lines.append(
            " | ".join(
                [
                    f"variable_name={row.get('variable_name', 'unknown')}",
                    f"dutch_definition={row.get('dutch_definition', 'unknown')}",
                    f"english_definition={row.get('english_definition', 'unknown')}",
                    f"dataset_name={row.get('dataset_name', 'unknown')}",
                    f"source_pdf={row.get('source_pdf', 'unknown')}",
                    f"page={row.get('page', 'unknown')}",
                    f"evidence={row.get('evidence_excerpt', row.get('raw_text_excerpt', 'unknown'))}",
                ]
            )
        )
    return "\n".join(lines)


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-ZÀ-ÿ0-9_]{4,}", text.lower())
        if token not in {"which", "with", "from", "that", "this", "study"}
    }


def score_catalog_row(row: dict, query_terms: set[str]) -> int:
    haystack = " ".join(str(value).lower() for value in row.values())
    return sum(1 for term in query_terms if term in haystack)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask CBS Guru from the command line.")
    parser.add_argument("question", help="Question to ask CBS Guru.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(ask_cbs_guru(args.question))


if __name__ == "__main__":
    main()
