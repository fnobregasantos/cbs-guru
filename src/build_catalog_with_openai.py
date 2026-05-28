"""Build a rough CBS variable catalog with OpenAI PDF extraction.

Run from the repository root:

    python src/build_catalog_with_openai.py --limit 5
    python src/build_catalog_with_openai.py --skip-existing

Large PDFs may be expensive or fail because the model must read substantial PDF
content. Use --limit for testing and keep the manifest for resumable progress.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from tqdm import tqdm

try:
    from prompts import CATALOG_EXTRACTION_PROMPT
except ModuleNotFoundError:
    from src.prompts import CATALOG_EXTRACTION_PROMPT


PDF_DIR = Path("data/raw_pdfs")
PROCESSED_DIR = Path("data/processed")
JSONL_PATH = PROCESSED_DIR / "variables_catalog_openai.jsonl"
CSV_PATH = PROCESSED_DIR / "variables_catalog.csv"
MANIFEST_PATH = PROCESSED_DIR / "openai_catalog_extraction_manifest.csv"

CATALOG_COLUMNS = [
    "variable_name",
    "dutch_definition",
    "english_definition",
    "dataset_name",
    "source_pdf",
    "source_url",
    "page",
    "granularity",
    "data_type",
    "example_value",
    "confidence",
    "evidence_excerpt",
    "extraction_notes",
]

MANIFEST_COLUMNS = [
    "pdf_filename",
    "local_path",
    "openai_file_id",
    "extraction_status",
    "n_variables",
    "error",
]


def main() -> None:
    load_dotenv()
    args = parse_args()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is missing. Add it to .env first.")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = Path(args.output)
    ensure_csv_header(csv_path)

    manifest = load_manifest()
    pdf_paths = sorted(Path(args.pdf_dir).rglob("*.pdf"))
    if args.skip_existing:
        pdf_paths = [
            path
            for path in pdf_paths
            if manifest.get(path.name, {}).get("extraction_status") != "completed"
        ]
    if args.limit:
        pdf_paths = pdf_paths[: args.limit]

    print(f"Model: {model}")
    print(f"PDFs queued: {len(pdf_paths)}")

    for pdf_path in tqdm(pdf_paths, desc="Extracting PDFs"):
        try:
            file_data = upload_file(api_key, pdf_path)
            file_id = file_data["id"]
            parsed = extract_catalog_from_pdf(api_key, model, file_id, pdf_path.name)
            records = normalize_catalog_records(parsed, pdf_path.name)
            append_jsonl(pdf_path.name, parsed, records)
            append_csv(records, csv_path)
            manifest[pdf_path.name] = {
                "pdf_filename": pdf_path.name,
                "local_path": str(pdf_path),
                "openai_file_id": file_id,
                "extraction_status": "completed",
                "n_variables": str(len(records)),
                "error": "",
            }
            print(f"{pdf_path.name}: completed, {len(records)} variables")
        except Exception as exc:
            manifest[pdf_path.name] = {
                "pdf_filename": pdf_path.name,
                "local_path": str(pdf_path),
                "openai_file_id": manifest.get(pdf_path.name, {}).get("openai_file_id", ""),
                "extraction_status": "failed",
                "n_variables": "0",
                "error": str(exc),
            }
            print(f"{pdf_path.name}: failed: {exc}")

        write_manifest(manifest)
        if args.sleep_seconds:
            time.sleep(args.sleep_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a rough variables catalog with OpenAI.")
    parser.add_argument("--pdf-dir", default=str(PDF_DIR), help="Directory containing PDFs.")
    parser.add_argument("--output", default=str(CSV_PATH), help="CSV output path.")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N PDFs.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip PDFs marked completed.")
    parser.add_argument("--sleep-seconds", type=float, default=1.0, help="Pause between PDFs.")
    return parser.parse_args()


def headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def json_headers(api_key: str) -> dict[str, str]:
    result = headers(api_key)
    result["Content-Type"] = "application/json"
    return result


def upload_file(api_key: str, pdf_path: Path) -> dict:
    with pdf_path.open("rb") as handle:
        response = requests.post(
            "https://api.openai.com/v1/files",
            headers=headers(api_key),
            files={"file": (pdf_path.name, handle, "application/pdf")},
            data={"purpose": "user_data"},
            timeout=180,
        )
    response.raise_for_status()
    return response.json()


def extract_catalog_from_pdf(api_key: str, model: str, file_id: str, pdf_filename: str) -> dict:
    user_prompt = (
        f"{CATALOG_EXTRACTION_PROMPT}\n\n"
        f"source_pdf filename provided by script: {pdf_filename}\n"
        "Return only JSON. Do not wrap it in Markdown."
    )
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_prompt},
                    {"type": "input_file", "file_id": file_id},
                ],
            }
        ],
        "temperature": 0,
    }
    data = post_response(api_key, payload)
    text = extract_response_text(data)
    return parse_json_from_text(text)


def post_response(api_key: str, payload: dict) -> dict:
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers=json_headers(api_key),
        json=payload,
        timeout=300,
    )
    if response.status_code == 400 and "temperature" in payload:
        payload = dict(payload)
        payload.pop("temperature", None)
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers=json_headers(api_key),
            json=payload,
            timeout=300,
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


def parse_json_from_text(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_catalog_records(parsed: dict, pdf_filename: str) -> list[dict[str, str]]:
    dataset_name = parsed.get("dataset_name") or "unknown"
    source_pdf = parsed.get("source_pdf") or pdf_filename
    records = []
    for variable in parsed.get("variables", []):
        record = {
            "variable_name": variable.get("variable_name", "unknown"),
            "dutch_definition": variable.get("dutch_definition", "unknown"),
            "english_definition": variable.get("english_definition", "unknown"),
            "dataset_name": dataset_name,
            "source_pdf": source_pdf,
            "source_url": "unknown",
            "page": str(variable.get("page", "unknown")),
            "granularity": variable.get("granularity", "unknown"),
            "data_type": variable.get("data_type", "unknown"),
            "example_value": variable.get("example_value", "unknown"),
            "confidence": str(variable.get("confidence", "unknown")),
            "evidence_excerpt": variable.get("evidence_excerpt", "unknown"),
            "extraction_notes": variable.get("extraction_notes", "unknown"),
        }
        records.append({key: clean_value(value) for key, value in record.items()})
    return records


def clean_value(value) -> str:
    if value is None or value == "":
        return "unknown"
    return str(value).replace("\n", " ").strip() or "unknown"


def ensure_csv_header(csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if csv_path.exists():
        return
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_COLUMNS)
        writer.writeheader()


def append_csv(records: list[dict[str, str]], csv_path: Path) -> None:
    with csv_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_COLUMNS)
        writer.writerows(records)


def append_jsonl(pdf_filename: str, parsed: dict, records: list[dict[str, str]]) -> None:
    with JSONL_PATH.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "source_pdf": pdf_filename,
                    "raw_response": parsed,
                    "records": records,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def load_manifest() -> dict[str, dict[str, str]]:
    if not MANIFEST_PATH.exists():
        return {}
    with MANIFEST_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {row["pdf_filename"]: row for row in reader}


def write_manifest(rows: dict[str, dict[str, str]]) -> None:
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for filename in sorted(rows):
            writer.writerow(rows[filename])


if __name__ == "__main__":
    main()
