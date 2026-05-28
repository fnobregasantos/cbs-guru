"""Extract candidate CBS variable records from local PDF documentation.

Run from the repository root:

    python src/extract_variables.py data/raw_pdfs/some_file.pdf

The extraction is intentionally heuristic. CBS PDFs vary by dataset, year, and
layout, so this script favors extractive transparency over perfect precision:
each candidate keeps its source PDF, page, confidence, method, and raw excerpt.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()


MANIFEST_PATH = Path("data/processed/pdf_manifest.csv")
TRANSLATION_CACHE_PATH = Path("data/processed/translation_cache.json")

VARIABLE_COLUMNS = [
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
    "extraction_method",
    "raw_text_excerpt",
]

EXCLUDED_VARIABLE_NAMES = {
    "DOCUMENTATIE",
    "VERSIE",
    "DATUM",
    "INHOUDSOPGAVE",
    "PAGINA",
    "VARIABELE",
    "VARIABELEN",
    "OMSCHRIJVING",
    "TOELICHTING",
    "CATEGORIE",
    "CATEGORIEEN",
    "CATEGORIEËN",
    "WAARDE",
    "WAARDEN",
    "CODE",
    "CODES",
    "TYPE",
    "LENGTE",
    "FORMAAT",
    "BRON",
    "BESTAND",
    "MICRODATA",
    "CBS",
    "DEFINITIE",
    "BIJLAGE",
    "TABEL",
    "TABELLEN",
    "INLEIDING",
    "ALGEMEEN",
    "OPMERKING",
    "OPMERKINGEN",
}

SECTION_HEADING_WORDS = {
    "inleiding",
    "inhoudsopgave",
    "documentatie",
    "versiegeschiedenis",
    "omschrijving",
    "populatie",
    "methodologie",
    "bijlage",
    "appendix",
    "referenties",
    "toelichting",
}

EXAMPLE_LABELS = (
    "waarde",
    "waarden",
    "code",
    "codes",
    "categorie",
    "categorieen",
    "categorieën",
)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def extract_variables_from_pdf(pdf_path, source_url=None) -> list[dict]:
    """Extract candidate variable records from one CBS PDF.

    Variable names and Dutch definitions are only taken from PDF text. Metadata
    such as granularity and type is inferred only from textual clues nearby.
    """
    pdf_path = Path(pdf_path)
    source_url = source_url or lookup_source_url(pdf_path)
    pages = extract_pages(pdf_path)
    first_page_text = pages[0][1] if pages else ""
    dataset_name = extract_dataset_name(first_page_text, str(pdf_path))

    records = []
    for page_number, page_text in pages:
        records.extend(
            extract_candidates_from_page(
                page_text=page_text,
                page_number=page_number,
                pdf_path=pdf_path,
                source_url=source_url,
                dataset_name=dataset_name,
            )
        )

    records = deduplicate_records(records)
    logging.info("Extracted %s candidate variables from %s.", len(records), pdf_path)
    return records


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise SystemExit(
            "pypdf is not installed. Run: pip install -r requirements.txt"
        ) from exc

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:
        raise SystemExit(f"Could not open PDF {pdf_path}: {exc}") from exc

    pages = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            logging.warning("Could not extract page %s from %s: %s", index, pdf_path, exc)
            text = ""
        pages.append((index, text))
    return pages


def extract_dataset_name(first_page_text: str, pdf_path: str) -> str:
    """Extract the dataset name from first-page 'Documentatie ...' text.

    If the PDF does not expose that pattern cleanly, fall back to the filename
    stem. The fallback is source-derived, not invented.
    """
    fallback = Path(pdf_path).stem.upper() or "unknown"
    text = clean_text(first_page_text)
    if not text:
        return fallback

    match = re.search(r"\bDocumentatie\s+(.{2,120})", text, flags=re.IGNORECASE)
    if not match:
        return fallback

    candidate = match.group(1)
    candidate = re.split(
        r"\b(versie|datum|pagina|inhoudsopgave|variabelen|omschrijving|cbs)\b",
        candidate,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    candidate = re.sub(r"[^A-Za-z0-9_ \-/]", " ", candidate)
    candidate = clean_text(candidate).strip(" -_/")
    if not candidate:
        return fallback

    words = candidate.split()
    if len(words) > 6:
        candidate = " ".join(words[:6])
    return candidate.upper()


def extract_candidates_from_page(
    page_text: str,
    page_number: int,
    pdf_path: Path,
    source_url: str,
    dataset_name: str,
) -> list[dict]:
    lines = clean_lines(page_text)
    records = []

    for index, line in enumerate(lines):
        if is_clear_section_heading(line):
            continue

        candidate = parse_candidate_line(line)
        if not candidate:
            continue

        variable_name, same_line_definition, method = candidate
        nearby_lines = next_description_lines(lines, index)
        definition = same_line_definition or " ".join(nearby_lines)
        definition = clean_definition(definition)

        if definition != "unknown":
            if same_line_definition and method == "same_line_variable_description":
                confidence = 0.95
                method = "same_line_variable_description"
            elif same_line_definition and method == "table_like_text":
                confidence = 0.75
            else:
                confidence = 0.85
                method = "standalone_variable_with_following_description"
        elif is_likely_variable_section(lines, index):
            confidence = 0.65
            method = "table_like_text"
        else:
            confidence = 0.45
            method = "candidate_without_definition"

        excerpt = make_excerpt(lines, index)
        granularity_context = " ".join([line, definition, dataset_name])
        data_type_context = " ".join([line, definition])
        records.append(
            {
                "variable_name": variable_name,
                "dutch_definition": definition,
                "english_definition": fallback_translation(definition),
                "dataset_name": dataset_name,
                "source_pdf": pdf_path.name,
                "source_url": source_url or "unknown",
                "page": str(page_number),
                "granularity": infer_granularity(granularity_context),
                "data_type": infer_data_type(data_type_context),
                "example_value": extract_example_value(nearby_lines),
                "confidence": f"{confidence:.2f}",
                "extraction_method": method,
                "raw_text_excerpt": excerpt,
            }
        )

    return records


def parse_candidate_line(line: str) -> tuple[str, str, str] | None:
    """Parse several common CBS variable layouts from one extracted line."""
    normalized = clean_text(line)
    if not normalized:
        return None
    if normalized.lower().startswith("documentatie "):
        return None

    patterns = (
        (r"^\d{1,4}\s+([A-Z][A-Z0-9_]{1,39})\s+(.{3,})$", "table_like_text"),
        (r"^([A-Z][A-Z0-9_]{1,39})\s+[-:]\s+(.{3,})$", "same_line_variable_description"),
        (r"^([A-Z][A-Z0-9_]{1,39})\s+(.{3,})$", "same_line_variable_description"),
        (r"^\d{1,4}\s+([A-Z][A-Z0-9_]{1,39})$", "standalone_variable_with_following_description"),
        (r"^([A-Z][A-Z0-9_]{1,39})$", "standalone_variable_with_following_description"),
    )

    for pattern, method in patterns:
        match = re.match(pattern, normalized)
        if not match:
            continue

        variable_name = match.group(1)
        if not is_valid_variable_name(variable_name):
            return None

        description = match.group(2).strip() if len(match.groups()) > 1 else ""
        description = strip_table_noise(description)
        if description and looks_like_non_definition(description):
            description = ""

        return variable_name, description, method

    # Flattened tables sometimes start with a label column before the variable.
    for token in re.findall(r"\b[A-Z][A-Z0-9_]{2,39}\b", normalized):
        if is_valid_variable_name(token) and not normalized.startswith(token):
            before, after = normalized.split(token, 1)
            if len(before.split()) <= 3 and after.strip():
                description = strip_table_noise(after)
                if description and not looks_like_non_definition(description):
                    return token, description, "table_like_text"

    return None


def is_valid_variable_name(name: str) -> bool:
    if name in EXCLUDED_VARIABLE_NAMES:
        return False
    if len(name) < 2 or len(name) > 40:
        return False
    if not re.match(r"^[A-Z][A-Z0-9_]*$", name):
        return False
    if name.isdigit():
        return False
    if len(name) <= 3 and not any(char.isdigit() for char in name):
        return False
    return True


def next_description_lines(lines: list[str], index: int) -> list[str]:
    descriptions = []
    for next_line in lines[index + 1 : index + 6]:
        if is_clear_section_heading(next_line):
            break
        if parse_candidate_line(next_line):
            break
        if looks_like_non_definition(next_line):
            continue
        descriptions.append(strip_table_noise(next_line))
    return [line for line in descriptions if line]


def is_clear_section_heading(line: str) -> bool:
    lower = line.lower().strip(" .:-")
    if lower in SECTION_HEADING_WORDS:
        return True
    if lower.startswith(("versiegeschiedenis", "inhoudsopgave", "bijlage")):
        return True
    return False


def is_likely_variable_section(lines: list[str], index: int) -> bool:
    window = " ".join(lines[max(0, index - 5) : index + 6]).lower()
    clues = ("variabele", "variabelen", "omschrijving", "definitie", "formaat", "type")
    return any(clue in window for clue in clues)


def looks_like_non_definition(text: str) -> bool:
    lower = text.lower().strip(" .:-")
    if not lower:
        return True
    if not re.search(r"[a-zA-ZÀ-ÿ]{3,}", text):
        return True
    if re.fullmatch(r"[.\-_\s]*\d{1,4}", text.strip()):
        return True
    if lower in SECTION_HEADING_WORDS:
        return True
    if lower.startswith(("toelichting bij", "codelijst", "versiegeschiedenis")):
        return True
    if lower in {"type", "lengte", "formaat", "waarde", "waarden", "code", "codes"}:
        return True
    if re.fullmatch(r"(?:[A-Z][A-Z0-9_]{1,39}\s*)+", text.strip()):
        return True
    if re.match(r"^pagina\s+\d+", lower):
        return True
    return False


def infer_granularity(text: str) -> str:
    lower = text.lower()
    checks = (
        (("rinpersoon", "persoons", "persoon"), "individual"),
        (("huishouden",), "household"),
        (("gemeente",), "municipality"),
        (("wijk",), "district/neighborhood"),
        (("buurt",), "neighborhood"),
        (("postcode",), "postcode"),
        (("adres",), "address"),
    )
    for clues, value in checks:
        if any(clue in lower for clue in clues):
            return value
    return "unknown"


def infer_data_type(text: str) -> str:
    lower = text.lower()
    if any(clue in lower for clue in ("datum", "date")):
        return "date"
    if any(clue in lower for clue in ("numeriek", "numeric", "getal", "integer")):
        return "numeric"
    if any(clue in lower for clue in ("bedrag", "euro", "inkomen")):
        return "numeric"
    if any(clue in lower for clue in ("tekst", "string", "alfanumeriek")):
        return "string"
    return "unknown"


def extract_example_value(nearby_lines: list[str]) -> str:
    for line in nearby_lines:
        lower = line.lower()
        if not any(label in lower for label in EXAMPLE_LABELS):
            continue

        explicit = re.search(
            r"\b(?:waarde|waarden|code|codes|categorie|categorieen|categorieën)\b"
            r"\s*[:\-]?\s*(.{1,120})",
            line,
            flags=re.IGNORECASE,
        )
        if explicit:
            value = clean_text(explicit.group(1)).strip(" .;")
            return value or "unknown"
    return "unknown"


def fallback_translation(dutch_definition: str) -> str:
    if dutch_definition == "unknown":
        return "unknown"
    return f"Translation pending: {dutch_definition}"


def translate_records(records: list[dict]) -> list[dict]:
    cache = load_translation_cache()
    changed = False
    has_credentials = bool(
        os.environ.get("OPENAI_API_KEY") and os.environ.get("OPENAI_TRANSLATION_MODEL")
    )
    if not has_credentials:
        logging.warning(
            "OPENAI_API_KEY and OPENAI_TRANSLATION_MODEL are required for uncached --translate calls."
        )

    for record in records:
        dutch_definition = record.get("dutch_definition", "unknown")
        if dutch_definition == "unknown":
            record["english_definition"] = "unknown"
            continue
        if dutch_definition in cache:
            record["english_definition"] = cache[dutch_definition]
            continue
        if not has_credentials:
            record["english_definition"] = fallback_translation(dutch_definition)
            continue

        translation = translate_definition_with_openai(dutch_definition)
        if translation:
            cache[dutch_definition] = translation
            record["english_definition"] = translation
            changed = True
        else:
            record["english_definition"] = fallback_translation(dutch_definition)

    if changed:
        save_translation_cache(cache)
    return records


def translate_definition_with_openai(dutch_definition: str) -> str | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_TRANSLATION_MODEL")
    if not api_key or not model:
        logging.warning(
            "OPENAI_API_KEY and OPENAI_TRANSLATION_MODEL are required for --translate."
        )
        return None

    prompt = (
        "Translate the following Dutch CBS variable definition into clear English.\n"
        "Do not add information.\n"
        "Do not infer meaning beyond the text.\n"
        "Preserve variable names, codes, numbers, and abbreviations.\n"
        "Return only the translation.\n\n"
        f"{dutch_definition}"
    )

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": prompt,
                "temperature": 0,
            },
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logging.warning("OpenAI translation failed: %s", exc)
        return None

    return extract_response_text(response.json())


def extract_response_text(response_data: dict) -> str | None:
    output_text = response_data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    for item in response_data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()

    return None


def load_translation_cache() -> dict[str, str]:
    if not TRANSLATION_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(TRANSLATION_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logging.warning("Could not read translation cache: %s", exc)
        return {}


def save_translation_cache(cache: dict[str, str]) -> None:
    TRANSLATION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRANSLATION_CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def deduplicate_records(records: list[dict]) -> list[dict]:
    best_by_variable = {}
    for record in records:
        key = (record["source_pdf"], record["variable_name"])
        current = best_by_variable.get(key)
        if current is None or is_better_record(record, current):
            best_by_variable[key] = record
    return list(best_by_variable.values())


def is_better_record(candidate: dict, current: dict) -> bool:
    candidate_confidence = float(candidate.get("confidence", 0))
    current_confidence = float(current.get("confidence", 0))
    if candidate_confidence != current_confidence:
        return candidate_confidence > current_confidence

    candidate_has_definition = candidate.get("dutch_definition") != "unknown"
    current_has_definition = current.get("dutch_definition") != "unknown"
    if candidate_has_definition != current_has_definition:
        return candidate_has_definition

    return int(candidate.get("page", 999999)) < int(current.get("page", 999999))


def clean_lines(text: str) -> list[str]:
    return [clean_text(line) for line in text.splitlines() if clean_text(line)]


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def clean_definition(text: str) -> str:
    text = strip_table_noise(text)
    text = re.sub(r"^(definitie|omschrijving)\s*[:\-]?\s*", "", text, flags=re.IGNORECASE)
    return text if text and not looks_like_non_definition(text) else "unknown"


def strip_table_noise(text: str) -> str:
    text = clean_text(text)
    text = text.strip("()[]{} ")
    text = re.sub(r"^(omschrijving|definitie|variabele|naam)\s*[:\-]?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\.{3,}\s*\d{1,4}\s*$", "", text)
    text = re.sub(r"\s+(type|lengte|formaat)\s*[:\-]?\s*\w+\s*$", "", text, flags=re.IGNORECASE)
    text = text.strip("()[]{} ")
    return clean_text(text)


def make_excerpt(lines: list[str], index: int, radius: int = 2) -> str:
    excerpt_lines = lines[max(0, index - radius) : index + radius + 1]
    excerpt = " | ".join(excerpt_lines)
    if len(excerpt) > 500:
        excerpt = excerpt[:497].rstrip() + "..."
    return excerpt or "unknown"


def lookup_source_url(pdf_path: Path) -> str:
    if not MANIFEST_PATH.exists():
        return "unknown"

    try:
        with MANIFEST_PATH.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if matches_manifest_row(pdf_path, row):
                    return row.get("pdf_url") or row.get("source_url") or "unknown"
    except OSError as exc:
        logging.warning("Could not read %s: %s", MANIFEST_PATH, exc)

    return "unknown"


def matches_manifest_row(pdf_path: Path, row: dict) -> bool:
    local_path = row.get("local_path", "")
    pdf_filename = row.get("pdf_filename", "")
    return (
        bool(local_path) and Path(local_path).name == pdf_path.name
    ) or (
        bool(pdf_filename) and pdf_filename == pdf_path.name
    )


def filter_by_confidence(records: list[dict], min_confidence: float) -> list[dict]:
    return [
        record
        for record in records
        if float(record.get("confidence", 0)) >= min_confidence
    ]


def write_csv(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=VARIABLE_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    logging.info("Wrote %s records to %s.", len(records), output_path)


def write_json(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logging.info("Wrote %s records to %s.", len(records), output_path)


def print_summary(
    pdf_path: Path,
    dataset_name: str,
    n_pages: int,
    records: list[dict],
    show_samples: int,
) -> None:
    with_dutch = sum(1 for record in records if record["dutch_definition"] != "unknown")
    with_english = sum(1 for record in records if record["english_definition"] != "unknown")

    print(f"PDF filename: {pdf_path.name}")
    print(f"Extracted dataset name: {dataset_name}")
    print(f"Number of pages: {n_pages}")
    print(f"Candidate variables found: {len(records)}")
    print(f"With Dutch definitions: {with_dutch}")
    print(f"With English definitions: {with_english}")

    if show_samples:
        print(f"\nTop {min(show_samples, len(records))} sample records:")
        for record in records[:show_samples]:
            print(
                "- "
                f"{record['variable_name']} "
                f"(page {record['page']}, confidence {record['confidence']}, "
                f"{record['extraction_method']}): "
                f"{record['dutch_definition']}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract candidate CBS variable records from a local PDF."
    )
    parser.add_argument("pdf_path", help="Path to a PDF in data/raw_pdfs/.")
    parser.add_argument(
        "--source-url",
        default=None,
        help="Optional source URL. If omitted, data/processed/pdf_manifest.csv is checked.",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Use OpenAI to translate extracted Dutch definitions, with cache.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Keep records at or above this confidence. Default: 0.0.",
    )
    parser.add_argument("--output", default=None, help="Optional CSV output path.")
    parser.add_argument("--json", default=None, help="Optional JSON output path.")
    parser.add_argument(
        "--show-samples",
        type=int,
        default=0,
        help="Print this many sample records after the summary.",
    )
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    pdf_path = Path(args.pdf_path)

    records = extract_variables_from_pdf(pdf_path, source_url=args.source_url)
    if args.translate:
        records = translate_records(records)
    records = filter_by_confidence(records, args.min_confidence)

    pages = extract_pages(pdf_path)
    dataset_name = extract_dataset_name(pages[0][1] if pages else "", str(pdf_path))

    if args.output:
        write_csv(records, Path(args.output))
    if args.json:
        write_json(records, Path(args.json))

    print_summary(
        pdf_path=pdf_path,
        dataset_name=dataset_name,
        n_pages=len(pages),
        records=records,
        show_samples=args.show_samples,
    )

    if not args.output and not args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
