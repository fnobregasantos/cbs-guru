# Legacy Streamlit prototype

These instructions reproduce the earlier Python/Streamlit prototype. They do not build the current website at **[www.cbsguru.org](https://www.cbsguru.org/)**.

The prototype uses the OpenAI Responses API with `file_search` over uploaded public CBS documentation PDFs. Its source and design notes are retained for research history and further development.

## Setup

Run these commands from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure `OPENAI_API_KEY` locally in `.env`. Do not commit the file or share the key.

1. Place public CBS documentation PDFs in `data/raw_pdfs/`.
2. Upload the documentation to an OpenAI vector store:

   ```bash
   python src/upload_openai_vector_store.py
   ```

3. Copy the printed vector store identifier into `OPENAI_VECTOR_STORE_ID` in `.env`.
4. Start the prototype:

   ```bash
   streamlit run app/streamlit_app.py
   ```

API calls and vector-store storage may incur charges. Only upload public documentation, not confidential CBS microdata or private research files.

## Conference URL

When the app runs at `cbs-guru.streamlit.app`, it displays a prominent link to **www.cbsguru.org** and attempts to redirect the top-level page. At other hostnames, including the usual local development address, it runs the earlier Streamlit interface. There is no separate legacy-mode switch.

## Optional configuration and catalog work

The retrieval code reads `OPENAI_API_KEY`, `OPENAI_VECTOR_STORE_ID` and `OPENAI_MODEL` from the environment; the app loads `.env` for local use. Setting `APP_PASSWORD` in the environment or Streamlit secrets enables its simple password gate outside the conference redirect route.

Source collection and catalog scripts include:

```bash
python src/scrape_cbs.py
python src/build_catalog.py
```

An alternative exploratory extraction workflow is available:

```bash
python src/build_catalog_with_openai.py --limit 30
```

Generated outputs and raw PDFs remain local unless deliberately prepared for publication. The prototype catalog is exploratory; verify candidates against the original Dutch documentation.

## Historical design notes

- [Architecture](architecture.md)
- [Prototype scope](demo_scope.md)
- [Prototype strategy](prototype_strategy.md)

These documents describe the earlier prototype and are not specifications for the current public website.

For presenting the current website, use the [live demo walkthrough](demo_script.md).
