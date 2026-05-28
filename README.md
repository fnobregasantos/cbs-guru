# CBS Guru

CBS Guru is a prototype research-support assistant for navigating public Statistics Netherlands (CBS) microdata documentation. The project explores how researchers can discover candidate variables, datasets, and documentation files through a lightweight Streamlit interface backed by retrieval over public CBS PDFs.

This repository supports an internal demonstration and reporting workflow for RPA PSI / University of Amsterdam. It is not production software and should be treated as an experimental workspace for ingestion, retrieval, catalog building, evaluation, and interface design.

The current interface is branded for the Dutch Institute for Emergent Phenomena (DIEP) and the University of Amsterdam Research Priority Area "Emergent Phenomena in Society: Polarization, Segregation and Inequality".

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

## Prototype Mode

The current prototype strategy uses OpenAI `file_search` over uploaded public CBS documentation PDFs. This lets the Streamlit app answer from source documents while the reviewed variable catalog is still being developed.

1. Put public CBS PDFs in `data/raw_pdfs/`.
2. Create `.env` with `OPENAI_API_KEY`.
3. Upload PDFs:

```bash
python src/upload_openai_vector_store.py
```

4. Copy the printed `OPENAI_VECTOR_STORE_ID` into `.env`.
5. Run the app:

```bash
streamlit run app/streamlit_app.py
```

Optional catalog extraction:

```bash
python src/build_catalog_with_openai.py --limit 30
```

## Public Demo Notes

The Streamlit app can be deployed as a password-protected prototype by setting these environment variables or Streamlit secrets:

- `OPENAI_API_KEY`
- `OPENAI_VECTOR_STORE_ID`
- `OPENAI_MODEL`
- `APP_PASSWORD`

Do not commit `.env`, API keys, passwords, raw PDFs, or generated private artifacts. Raw PDFs are excluded from Git and should be uploaded to OpenAI only when they are public CBS documentation files.

## Limitations

- CBS Guru is a prototype and may miss relevant variables or retrieve incomplete snippets.
- Suggested variables should be verified in the original CBS documentation before research use.
- The current variable catalog is exploratory and may contain imperfect candidates.
- The tool does not provide access to confidential CBS microdata.
- Source grounding currently depends on retrieved PDF snippets and/or the generated catalog, both of which require human review for final decisions.
- The app is intended to support exploration and discussion, not to replace official CBS documentation or statistical review.

## Roadmap

Planned improvements over the next phase of the project:

- Build a reviewed and versioned `variables_catalog.csv` from the public CBS documentation.
- Improve page-level source citation, evidence extraction, and source-check tables.
- Add systematic evaluation questions, regression checks, and expert review notes.
- Add stronger safeguards so recommendations are limited to retrieved PDF evidence or reviewed catalog entries.
- Improve local PDF parsing and parallel processing for faster catalog updates.
- Add clearer metadata for datasets, granularity, years, temporal coverage, and known limitations.
- Explore a more robust deployment and authentication workflow for broader research use.
- Document a reproducible workflow for updating the document collection and catalog.

## Notes

Raw PDFs should stay in `data/raw_pdfs/` and are intentionally excluded from Git. Generated binary artifacts in `data/processed/` should also stay local unless a specific artifact is approved for sharing.
