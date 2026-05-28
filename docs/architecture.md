# Architecture

CBS Guru is organized as a lightweight prototype pipeline for retrieval over public CBS documentation PDFs and exploratory variable catalog building.

## Components

- Link collection: source URLs and crawl inputs live in `data/raw_links/`.
- Raw document storage: public CBS PDFs are kept locally in `data/raw_pdfs/` and excluded from Git.
- OpenAI vector store upload: `src/upload_openai_vector_store.py` uploads public PDFs for `file_search`.
- Retrieval engine: `src/guru_engine.py` calls the OpenAI Responses API with `file_search`.
- Optional catalog extraction: `src/build_catalog_with_openai.py` creates an exploratory variable catalog.
- Demo app: Streamlit interface code lives in `app/`.
- Evaluation: prompt sets, expected behaviors, and review notes should live in `evaluation/`.

## Data Flow

1. Collect source links.
2. Download or place public CBS PDFs in `data/raw_pdfs/`.
3. Upload PDFs to an OpenAI vector store.
4. Store the vector store id in `.env` or deployment secrets.
5. Query the vector store from the Streamlit app through the Responses API.
6. Optionally generate an exploratory `variables_catalog.csv`.
7. Record demo observations and answer quality checks in `evaluation/`.

## Prototype Constraints

The current structure is intended for a research prototype. It favors clarity and fast iteration over production concerns such as distributed storage, background jobs, observability, institutional authentication, and formal release management.

## Safety Boundaries

- Raw PDFs, API keys, passwords, and `.env` files should not be committed.
- The app should only use public CBS documentation PDFs.
- Recommendations should remain grounded in retrieved PDF evidence and/or a reviewed catalog.
- The prototype does not provide access to confidential CBS microdata.
