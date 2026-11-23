# Prototype strategy

> Historical strategy for the earlier Streamlit prototype. It does not describe the current live website implementation. See the [project overview](../README.md) for the current pilot; website source is held for a separate release.

CBS Guru currently uses OpenAI `file_search` over uploaded public CBS documentation PDFs. This gives the prototype a practical way to answer questions from source documents while the reviewed variable catalog and evaluation workflow are still being developed.

The goal is to support research discussion and scoping, not to replace official CBS documentation or expert review.

## Pipeline

1. Place public CBS documentation PDFs in `data/raw_pdfs/`.
2. Upload the PDFs to an OpenAI vector store.
3. Query the PDFs through the OpenAI Responses API with `file_search`.
4. Optionally build a rough `variables_catalog.csv` using OpenAI-assisted PDF extraction.
5. Review and validate important variables against the original CBS documentation.

## Limitations

- The prototype may miss relevant variables.
- The prototype may retrieve incomplete or imperfect snippets.
- Suggested variables must be verified in the official CBS documentation.
- The current catalog extraction is intended to support exploration, not final scientific evidence.
- The tool does not provide access to confidential CBS microdata.

## Planned improvements

- Build a reviewed and versioned variable catalog.
- Improve page-level source citation and evidence extraction.
- Add systematic evaluation questions and regression checks.
- Add stronger safeguards so recommendations are limited to retrieved PDF evidence or reviewed catalog entries.
- Improve local PDF parsing and parallel processing for faster catalog updates.
- Add clearer metadata for datasets, granularity, years, and known limitations.
- Prepare a more robust deployment and documentation workflow for research use.
- Document a six-month work plan for validation, review, deployment, and maintenance.
