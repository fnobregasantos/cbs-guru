"""Upload CBS PDF documentation to an OpenAI vector store.

Run from the repository root:

    python src/upload_openai_vector_store.py
    python src/upload_openai_vector_store.py --limit 10
    python src/upload_openai_vector_store.py --force
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from dotenv import load_dotenv
from tqdm import tqdm


PDF_DIR = Path("data/raw_pdfs")
PROCESSED_DIR = Path("data/processed")
MANIFEST_PATH = PROCESSED_DIR / "openai_vector_store_manifest.csv"
SUMMARY_PATH = PROCESSED_DIR / "openai_vector_store.json"
DEFAULT_VECTOR_STORE_NAME = "CBS Guru PDF Store"
VECTOR_STORE_PLACEHOLDERS = {"", "created_after_upload", "your_vector_store_id_here"}

MANIFEST_COLUMNS = [
    "pdf_filename",
    "local_path",
    "openai_file_id",
    "vector_store_id",
    "upload_status",
    "error",
]


def main() -> None:
    load_dotenv()
    args = parse_args()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is missing. Add it to .env first.")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    vector_store_name = os.environ.get("OPENAI_VECTOR_STORE_NAME", DEFAULT_VECTOR_STORE_NAME)
    vector_store_id = clean_vector_store_id(os.environ.get("OPENAI_VECTOR_STORE_ID"))
    if vector_store_id:
        print(f"Using existing vector store: {vector_store_id}")
    else:
        vector_store = create_vector_store(api_key, vector_store_name)
        vector_store_id = vector_store["id"]
        print(f"Created vector store: {vector_store_id}")

    existing_rows = load_manifest()
    pdf_paths = sorted(PDF_DIR.rglob("*.pdf"))
    if args.limit:
        pdf_paths = pdf_paths[: args.limit]

    upload_jobs = []
    skipped = 0
    for pdf_path in pdf_paths:
        previous = existing_rows.get(pdf_path.name)
        if previous and not args.force and previous.get("upload_status") == "completed":
            if previous.get("vector_store_id") == vector_store_id:
                print(f"Skipping already uploaded: {pdf_path.name}")
                skipped += 1
                continue
        upload_jobs.append((pdf_path, previous))

    attempted = len(upload_jobs)
    uploaded = skipped
    failed = 0

    if args.workers <= 1:
        for pdf_path, previous in tqdm(upload_jobs, desc="Uploading PDFs"):
            row = upload_one_pdf(api_key, vector_store_id, pdf_path, previous)
            if row["upload_status"] == "completed":
                uploaded += 1
            else:
                failed += 1
            existing_rows[pdf_path.name] = row
            print_status(row)
            write_manifest(existing_rows)
    else:
        print(f"Uploading with {args.workers} workers.")
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(upload_one_pdf, api_key, vector_store_id, pdf_path, previous): pdf_path
                for pdf_path, previous in upload_jobs
            }
            for future in tqdm(as_completed(futures), total=len(futures), desc="Uploading PDFs"):
                row = future.result()
                if row["upload_status"] == "completed":
                    uploaded += 1
                else:
                    failed += 1
                existing_rows[row["pdf_filename"]] = row
                print_status(row)
                write_manifest(existing_rows)

    write_manifest(existing_rows)
    write_summary(
        vector_store_id=vector_store_id,
        vector_store_name=vector_store_name,
        attempted=attempted,
        uploaded=uploaded,
        failed=failed,
    )

    print("\nUpload summary")
    print(f"Vector store ID: {vector_store_id}")
    print(f"Files attempted: {attempted}")
    print(f"Files uploaded/completed: {uploaded}")
    print(f"Files skipped: {skipped}")
    print(f"Files failed: {failed}")
    print("\nAdd this to your .env:")
    print(f"OPENAI_VECTOR_STORE_ID={vector_store_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload local CBS PDFs to OpenAI file_search.")
    parser.add_argument("--force", action="store_true", help="Re-upload files already in the manifest.")
    parser.add_argument("--limit", type=int, default=None, help="Upload only the first N PDFs.")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Parallel upload workers. Start with 2-4 to avoid rate limit issues.",
    )
    return parser.parse_args()


def clean_vector_store_id(value: str | None) -> str:
    value = (value or "").strip()
    if value in VECTOR_STORE_PLACEHOLDERS:
        return ""
    return value


def upload_one_pdf(
    api_key: str,
    vector_store_id: str,
    pdf_path: Path,
    previous: dict[str, str] | None,
) -> dict[str, str]:
    openai_file_id = previous.get("openai_file_id", "") if previous else ""
    try:
        file_data = upload_file(api_key, pdf_path)
        openai_file_id = file_data["id"]
        attach_file_to_vector_store(api_key, vector_store_id, openai_file_id)
        vector_file = poll_vector_store_file(api_key, vector_store_id, openai_file_id)
        status = vector_file.get("status", "unknown")
        error = json.dumps(vector_file.get("last_error")) if vector_file.get("last_error") else ""
        return row_for_pdf(
            pdf_path=pdf_path,
            openai_file_id=openai_file_id,
            vector_store_id=vector_store_id,
            upload_status=status,
            error=error,
        )
    except Exception as exc:
        return row_for_pdf(
            pdf_path=pdf_path,
            openai_file_id=openai_file_id,
            vector_store_id=vector_store_id,
            upload_status="failed",
            error=str(exc),
        )


def print_status(row: dict[str, str]) -> None:
    if row["upload_status"] == "failed":
        print(f"{row['pdf_filename']}: failed: {row['error']}")
    else:
        print(f"{row['pdf_filename']}: {row['upload_status']}")


def api_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "assistants=v2",
    }


def json_headers(api_key: str) -> dict[str, str]:
    headers = api_headers(api_key)
    headers["Content-Type"] = "application/json"
    return headers


def create_vector_store(api_key: str, name: str) -> dict:
    response = requests.post(
        "https://api.openai.com/v1/vector_stores",
        headers=json_headers(api_key),
        json={"name": name},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def upload_file(api_key: str, pdf_path: Path) -> dict:
    with pdf_path.open("rb") as handle:
        response = requests.post(
            "https://api.openai.com/v1/files",
            headers=api_headers(api_key),
            files={"file": (pdf_path.name, handle, "application/pdf")},
            data={"purpose": "assistants"},
            timeout=180,
        )
    response.raise_for_status()
    return response.json()


def attach_file_to_vector_store(api_key: str, vector_store_id: str, file_id: str) -> dict:
    response = requests.post(
        f"https://api.openai.com/v1/vector_stores/{vector_store_id}/files",
        headers=json_headers(api_key),
        json={"file_id": file_id},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def poll_vector_store_file(api_key: str, vector_store_id: str, file_id: str) -> dict:
    for _ in range(120):
        response = requests.get(
            f"https://api.openai.com/v1/vector_stores/{vector_store_id}/files/{file_id}",
            headers=api_headers(api_key),
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") in {"completed", "failed", "cancelled"}:
            return data
        time.sleep(2)
    return {"status": "timeout", "last_error": "Timed out waiting for vector store processing."}


def load_manifest() -> dict[str, dict[str, str]]:
    if not MANIFEST_PATH.exists():
        return {}
    with MANIFEST_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {row["pdf_filename"]: row for row in reader}


def row_for_pdf(
    pdf_path: Path,
    openai_file_id: str,
    vector_store_id: str,
    upload_status: str,
    error: str,
) -> dict[str, str]:
    return {
        "pdf_filename": pdf_path.name,
        "local_path": str(pdf_path),
        "openai_file_id": openai_file_id,
        "vector_store_id": vector_store_id,
        "upload_status": upload_status,
        "error": error,
    }


def write_manifest(rows_by_filename: dict[str, dict[str, str]]) -> None:
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for filename in sorted(rows_by_filename):
            writer.writerow(rows_by_filename[filename])


def write_summary(
    vector_store_id: str,
    vector_store_name: str,
    attempted: int,
    uploaded: int,
    failed: int,
) -> None:
    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "vector_store_id": vector_store_id,
                "vector_store_name": vector_store_name,
                "n_files_attempted": attempted,
                "n_files_uploaded": uploaded,
                "n_files_failed": failed,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
