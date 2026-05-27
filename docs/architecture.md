# Architecture

CBS Guru is organized as a lightweight prototype pipeline.

## Components

- Link collection: source URLs and crawl inputs live in `data/raw_links/`.
- Raw document storage: PDFs are kept locally in `data/raw_pdfs/` and excluded from Git.
- Processing: extraction and transformation code should live in `src/`, with derived outputs written to `data/processed/`.
- Demo app: Streamlit interface code should live in `app/`.
- Evaluation: prompt sets, expected behaviors, and review notes should live in `evaluation/`.

## Data Flow

1. Collect source links.
2. Download or place source PDFs in `data/raw_pdfs/`.
3. Extract text and metadata into `data/processed/`.
4. Use processed content from the app or notebooks.
5. Record demo observations and answer quality checks in `evaluation/`.

## Prototype Constraints

The current structure is intended for an internal demo. It favors clarity and fast iteration over production concerns such as distributed storage, background jobs, observability, and formal release management.
