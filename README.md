# CBS Guru

CBS Guru is a prototype for an internal demo that explores how CBS source material can be collected, processed, and queried through a lightweight assistant-style interface.

The repository is intentionally minimal while the demo scope is being validated. It is not production software and should be treated as an experimental workspace for ingestion, retrieval, evaluation, and Streamlit app development.

## Repository Layout

- `data/raw_links/`: source link lists and crawl inputs
- `data/raw_pdfs/`: local raw PDFs, excluded from Git
- `data/processed/`: derived text, metadata, and temporary processed outputs
- `notebooks/`: exploration and analysis notebooks
- `src/`: reusable ingestion, processing, and retrieval code
- `app/`: demo application code
- `docs/`: design notes, architecture, and demo materials
- `evaluation/`: test questions, evaluation notes, and demo quality checks

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add required local configuration, including `OPENAI_API_KEY`, to `.env`.

## Notes

Raw PDFs should stay in `data/raw_pdfs/` and are intentionally excluded from Git. Generated binary artifacts in `data/processed/` should also stay local unless a specific artifact is approved for sharing.
