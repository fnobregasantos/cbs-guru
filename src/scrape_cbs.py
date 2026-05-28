"""Scrape CBS microdata dataset pages and build a PDF manifest.

Run from the repository root:

    python src/scrape_cbs.py
    python src/scrape_cbs.py --download
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


CATALOG_URL = (
    "https://www.cbs.nl/nl-nl/onze-diensten/maatwerk-en-microdata/"
    "microdata-zelf-onderzoek-doen/catalogus-microdata"
)

RAW_LINKS_PATH = Path("data/raw_links/dataset_links.txt")
RAW_PDFS_DIR = Path("data/raw_pdfs")
MANIFEST_PATH = Path("data/processed/pdf_manifest.csv")

MANIFEST_COLUMNS = [
    "dataset_url",
    "pdf_url",
    "pdf_filename",
    "local_path",
    "extraction_status",
    "n_variables",
]

REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 1


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def fetch_soup(url: str) -> BeautifulSoup | None:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logging.warning("Could not fetch %s: %s", url, exc)
        return None

    return BeautifulSoup(response.content, "html.parser")


def sanitize_filename(name: str) -> str:
    name = unquote(name).strip()
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = re.sub(r"\s+", " ", name)
    return name or "unknown.pdf"


def pdf_filename_from_url(pdf_url: str) -> str:
    parsed = urlparse(pdf_url)
    filename = Path(parsed.path).name
    filename = sanitize_filename(filename)
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"
    return filename


def get_category_links(catalog_url: str = CATALOG_URL) -> list[str]:
    soup = fetch_soup(catalog_url)
    if soup is None:
        return []

    category_links = set()
    for link in soup.find_all("a", href=True):
        full_url = urljoin(catalog_url, link["href"])
        if "/catalogus-microdata/" in full_url and full_url != catalog_url:
            category_links.add(full_url)

    logging.info("Found %s category links.", len(category_links))
    return sorted(category_links)


def get_dataset_links_from_category(category_url: str) -> list[str]:
    soup = fetch_soup(category_url)
    if soup is None:
        return []

    dataset_links = set()
    for link in soup.find_all("a", href=True):
        full_url = urljoin(category_url, link["href"])
        if "/microdatabestanden/" in full_url:
            dataset_links.add(full_url)

    logging.info("Found %s dataset links in %s.", len(dataset_links), category_url)
    return sorted(dataset_links)


def read_dataset_links(path: Path = RAW_LINKS_PATH) -> list[str]:
    if not path.exists():
        return []

    links = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#"):
                links.append(line)

    logging.info("Read %s dataset links from %s.", len(links), path)
    return sorted(set(links))


def write_dataset_links(dataset_links: list[str], path: Path = RAW_LINKS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for link in sorted(set(dataset_links)):
            handle.write(f"{link}\n")
    logging.info("Wrote %s dataset links to %s.", len(dataset_links), path)


def discover_dataset_links() -> list[str]:
    existing_links = read_dataset_links()
    if existing_links:
        return existing_links

    logging.info("No existing dataset link file found. Scraping CBS catalog.")
    all_dataset_links = set()
    for category_url in get_category_links():
        all_dataset_links.update(get_dataset_links_from_category(category_url))
        time.sleep(REQUEST_DELAY_SECONDS)

    dataset_links = sorted(all_dataset_links)
    write_dataset_links(dataset_links)
    return dataset_links


def get_pdf_links(dataset_url: str) -> list[str]:
    soup = fetch_soup(dataset_url)
    if soup is None:
        return []

    pdf_links = set()
    pdf_pattern = re.compile(r"\.pdf($|\?)", re.IGNORECASE)
    for link in soup.find_all("a", href=True):
        href = link["href"]
        full_url = urljoin(dataset_url, href)
        link_text = link.get_text(" ", strip=True).lower()
        if pdf_pattern.search(full_url) or "pdf" in link_text:
            pdf_links.add(full_url)

    return sorted(pdf_links)


def count_variables_in_pdf(pdf_path: Path) -> tuple[str, str]:
    if not pdf_path.exists():
        return "not_downloaded", "unknown"

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    except ImportError:
        logging.warning("pypdf is not installed; cannot inspect %s.", pdf_path)
        return "missing_pypdf", "unknown"
    except Exception as exc:
        logging.warning("Could not extract text from %s: %s", pdf_path, exc)
        return "error", "unknown"

    text = "\n".join(text_parts)
    n_variables = count_variable_headings(text)
    return "extracted", str(n_variables)


def count_variable_headings(text: str) -> int:
    in_variables_section = False
    variables = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "Toelichting op de variabelen" in line:
            in_variables_section = True
            continue
        if "Versiegeschiedenis" in line:
            in_variables_section = False
            continue
        if in_variables_section:
            match = re.match(r"^(\d+)\s+(\w+)", line)
            if match:
                variables.add((match.group(1), match.group(2)))

    return len(variables)


def download_pdf(pdf_url: str, local_path: Path) -> bool:
    if local_path.exists():
        logging.info("Already downloaded: %s", local_path)
        return True

    try:
        response = requests.get(pdf_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logging.warning("Could not download %s: %s", pdf_url, exc)
        return False

    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(response.content)
    logging.info("Downloaded %s", local_path)
    return True


def load_existing_manifest(path: Path = MANIFEST_PATH) -> dict[tuple[str, str], dict[str, str]]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            (row.get("dataset_url", ""), row.get("pdf_url", "")): row
            for row in reader
        }


def write_manifest(rows: list[dict[str, str]], path: Path = MANIFEST_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    logging.info("Wrote %s manifest rows to %s.", len(rows), path)


def build_manifest(download: bool) -> None:
    RAW_PDFS_DIR.mkdir(parents=True, exist_ok=True)
    dataset_links = discover_dataset_links()
    existing_rows = load_existing_manifest()
    manifest_rows = []

    logging.info("Processing %s dataset pages.", len(dataset_links))
    for index, dataset_url in enumerate(dataset_links, start=1):
        logging.info("Processing dataset %s/%s: %s", index, len(dataset_links), dataset_url)
        pdf_links = get_pdf_links(dataset_url)
        logging.info("Found %s PDF links.", len(pdf_links))

        for pdf_url in pdf_links:
            pdf_filename = pdf_filename_from_url(pdf_url)
            local_path = RAW_PDFS_DIR / pdf_filename

            if download:
                download_pdf(pdf_url, local_path)

            extraction_status, n_variables = count_variables_in_pdf(local_path)
            row = {
                "dataset_url": dataset_url,
                "pdf_url": pdf_url,
                "pdf_filename": pdf_filename,
                "local_path": str(local_path),
                "extraction_status": extraction_status,
                "n_variables": n_variables,
            }
            existing_rows[(dataset_url, pdf_url)] = row

        time.sleep(REQUEST_DELAY_SECONDS)

    manifest_rows = [
        existing_rows[key]
        for key in sorted(existing_rows)
    ]
    write_manifest(manifest_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a CBS microdata PDF manifest from dataset pages."
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download discovered PDFs into data/raw_pdfs/.",
    )
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    build_manifest(download=args.download)


if __name__ == "__main__":
    main()
