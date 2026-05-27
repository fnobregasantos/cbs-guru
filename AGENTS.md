# AGENTS.md

## Project

CBS Guru is a Streamlit prototype that helps researchers discover candidate CBS microdata variables from Dutch CBS documentation.

The goal is an internal demo for RPA PSI / University of Amsterdam, plus a public GitHub repository for reporting.

## Main rules

- Do not invent CBS variables.
- Do not invent dataset names.
- Do not invent source PDF filenames.
- Recommended variables must come from data/processed/variables_catalog.csv.
- If information is missing, write "unknown".
- Keep raw PDFs out of Git.
- Use the OpenAI Responses API, not the Assistants API.
- Prefer simple, readable Python over complex architecture.
- Make scripts runnable from the repository root.
- Use Streamlit for the first app, not React or FastAPI.

## Expected project structure

data/raw_links/
data/raw_pdfs/
data/processed/
notebooks/
src/
app/
docs/
evaluation/

## Important commands

Run scraper:

python src/scrape_cbs.py

Build catalog:

python src/build_catalog.py

Run app:

streamlit run app/streamlit_app.py

## Demo goal

The app should answer questions like:

"Which CBS variables can help study residential segregation, migration background, and income inequality in Amsterdam neighborhoods?"

The answer should include:

- relevant CBS variables
- Dutch variable names
- Dutch definitions
- English translations
- source PDFs
- likely granularity
- suggested research use
- limitations
- source-check table