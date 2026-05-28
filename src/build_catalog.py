"""Build the CBS Guru variable catalog from local PDFs.

Run from the repository root:

    python src/build_catalog.py
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

try:
    from extract_variables import VARIABLE_COLUMNS, extract_variables_from_pdf
except ModuleNotFoundError:
    from src.extract_variables import VARIABLE_COLUMNS, extract_variables_from_pdf


RAW_PDFS_DIR = Path("data/raw_pdfs")
PROCESSED_DIR = Path("data/processed")
MANIFEST_PATH = PROCESSED_DIR / "pdf_manifest.csv"
CATALOG_CSV_PATH = PROCESSED_DIR / "variables_catalog.csv"
CATALOG_JSON_PATH = PROCESSED_DIR / "variables_catalog.json"

MANIFEST_COLUMNS = [
    "dataset_url",
    "pdf_url",
    "pdf_filename",
    "local_path",
    "extraction_status",
    "n_variables",
]


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    setup_logging()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    manifest_rows = load_manifest()
    pdf_paths = sorted(RAW_PDFS_DIR.rglob("*.pdf"))

    logging.info("Found %s PDFs in %s.", len(pdf_paths), RAW_PDFS_DIR)

    all_records = []
    failed_pdfs = 0

    for index, pdf_path in enumerate(pdf_paths, start=1):
        logging.info("Processing PDF %s/%s: %s", index, len(pdf_paths), pdf_path)
        source_url = source_url_for_pdf(pdf_path, manifest_rows)

        try:
            records = extract_variables_from_pdf(pdf_path, source_url=source_url)
        except SystemExit as exc:
            failed_pdfs += 1
            logging.warning("Extraction failed for %s: %s", pdf_path, exc)
            update_manifest_for_pdf(
                manifest_rows=manifest_rows,
                pdf_path=pdf_path,
                extraction_status="failed",
                n_variables="0",
            )
            continue
        except Exception as exc:
            failed_pdfs += 1
            logging.warning("Extraction failed for %s: %s", pdf_path, exc)
            update_manifest_for_pdf(
                manifest_rows=manifest_rows,
                pdf_path=pdf_path,
                extraction_status="failed",
                n_variables="0",
            )
            continue

        normalized_records = [normalize_record(record, pdf_path) for record in records]
        all_records.extend(normalized_records)
        update_manifest_for_pdf(
            manifest_rows=manifest_rows,
            pdf_path=pdf_path,
            extraction_status="extracted",
            n_variables=str(len(normalized_records)),
        )

    catalog_records = deduplicate_records(all_records)
    write_catalog_csv(catalog_records)
    write_catalog_json(catalog_records)
    write_manifest(manifest_rows)

    print(f"PDFs processed: {len(pdf_paths)}")
    print(f"PDFs failed: {failed_pdfs}")
    print(f"Variable records extracted: {len(catalog_records)}")


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []

    with MANIFEST_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append({column: row.get(column, "unknown") or "unknown" for column in MANIFEST_COLUMNS})
        return rows


def source_url_for_pdf(pdf_path: Path, manifest_rows: list[dict]) -> str:
    for row in matching_manifest_rows(pdf_path, manifest_rows):
        pdf_url = row.get("pdf_url", "unknown")
        if pdf_url and pdf_url != "unknown":
            return pdf_url
    return "unknown"


def matching_manifest_rows(pdf_path: Path, manifest_rows: list[dict]) -> list[dict]:
    matches = []
    for row in manifest_rows:
        local_path = row.get("local_path", "")
        pdf_filename = row.get("pdf_filename", "")
        if local_path and Path(local_path).name == pdf_path.name:
            matches.append(row)
        elif pdf_filename and pdf_filename == pdf_path.name:
            matches.append(row)
    return matches


def update_manifest_for_pdf(
    manifest_rows: list[dict],
    pdf_path: Path,
    extraction_status: str,
    n_variables: str,
) -> None:
    matches = matching_manifest_rows(pdf_path, manifest_rows)
    if not matches:
        matches = [new_manifest_row(pdf_path)]
        manifest_rows.extend(matches)

    for row in matches:
        if not row.get("pdf_filename") or row.get("pdf_filename") == "unknown":
            row["pdf_filename"] = pdf_path.name
        if not row.get("local_path") or row.get("local_path") == "unknown":
            row["local_path"] = str(pdf_path)
        row["extraction_status"] = extraction_status
        row["n_variables"] = n_variables
        for column in MANIFEST_COLUMNS:
            if not row.get(column):
                row[column] = "unknown"


def new_manifest_row(pdf_path: Path) -> dict:
    return {
        "dataset_url": "unknown",
        "pdf_url": "unknown",
        "pdf_filename": pdf_path.name,
        "local_path": str(pdf_path),
        "extraction_status": "unknown",
        "n_variables": "unknown",
    }


def normalize_record(record: dict, pdf_path: Path) -> dict:
    normalized = {}
    for column in VARIABLE_COLUMNS:
        value = record.get(column, "unknown")
        normalized[column] = value if value not in (None, "") else "unknown"

    normalized["source_pdf"] = normalized.get("source_pdf") or pdf_path.name
    if normalized["source_pdf"] == "unknown":
        normalized["source_pdf"] = pdf_path.name

    return normalized


def deduplicate_records(records: list[dict]) -> list[dict]:
    seen = set()
    unique_records = []

    for record in records:
        key = (
            normalize_key(record.get("variable_name", "unknown")),
            normalize_key(record.get("dutch_definition", "unknown")),
            normalize_key(record.get("source_pdf", "unknown")),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(record)

    return unique_records


def normalize_key(value: str) -> str:
    return " ".join(str(value).lower().split())


def write_catalog_csv(records: list[dict]) -> None:
    with CATALOG_CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=VARIABLE_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    logging.info("Wrote %s records to %s.", len(records), CATALOG_CSV_PATH)


def write_catalog_json(records: list[dict]) -> None:
    CATALOG_JSON_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logging.info("Wrote %s records to %s.", len(records), CATALOG_JSON_PATH)


def write_manifest(manifest_rows: list[dict]) -> None:
    sorted_rows = sorted(
        manifest_rows,
        key=lambda row: (
            row.get("pdf_filename", "unknown"),
            row.get("pdf_url", "unknown"),
            row.get("dataset_url", "unknown"),
        ),
    )

    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for row in sorted_rows:
            writer.writerow(
                {
                    column: row.get(column, "unknown") or "unknown"
                    for column in MANIFEST_COLUMNS
                }
            )

    logging.info("Updated %s.", MANIFEST_PATH)


if __name__ == "__main__":
    main()
