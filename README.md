# CBS Guru

**[Open CBS Guru at www.cbsguru.org](https://www.cbsguru.org/)**

[Plan my project](https://www.cbsguru.org/plan.html) · [Ask the tutor](https://www.cbsguru.org/tutor.html) · [Search variables](https://www.cbsguru.org/variables.html) · [Browse datasets](https://www.cbsguru.org/datasets.html)

CBS Guru helps researchers explore public Statistics Netherlands (CBS) microdata documentation in English while keeping the exact Dutch dataset codes, variable names and code values needed for research. It combines translated documentation, a concept map and AI explanations to help identify candidate data for a project.

This is an independent research pilot developed by the **Dutch Institute for Emergent Phenomena (DIEP)** within the University of Amsterdam Research Priority Area **Emergent Phenomena in Society: Polarization, Segregation and Inequality (RPA PSI)**. It is not affiliated with or endorsed by CBS and does not provide access to confidential microdata.

## Try the live pilot

- **Search and browse:** search in English or Dutch, inspect definitions and code lists, and follow links to the original Dutch PDF and page. Collect variables in a browser-local basket and export CSV, an R vector or a Python list.
- **Plan a project:** paste an abstract to obtain concept-map matches, then optionally ask AI to explain their research use and limitations. The concept-map shortlist highlights up to five complementary measures, explains its rule-based ordering and flags known year mismatches.
- **Inspect dataset connections:** explore a graph with exact linking keys, candidate routes and missing bridge documentation. These are research leads; the graph does not establish that a join is valid or that access is available.
- **Ask the tutor:** ask focused questions about definitions, possible measures and limitations, with explanations and citations to check against the source documentation.
- **Check a translation:** compare an English passage with the Dutch original, confirm it, suggest a correction or mark uncertainty. Feedback applies to that passage and version. Dutch proficiency is self-declared; corrections are moderated before publication.

For a quick demonstration, open **[Plan my project](https://www.cbsguru.org/plan.html)**, choose **Income inequality** under **Presentation example**, and select **Load the example**. Inspect the shortlist and then the dataset connections. A [live demo walkthrough](docs/demo_script.md) gives the full sequence.

## Coverage and limitations

The **23 November 2026 release** contains **411 translated documents** from a source collection of **687 documents**, with **23,072 variable entries**. This is partial coverage, not a complete inventory of CBS microdata.

The English documentation is AI-translated. Automatic checks help preserve identifiers and source structure; they do not establish translation accuracy. No full-page human reviews were recorded at release, and community passage feedback is reported separately.

AI recommendations can be wrong even when a variable name exists in the catalog. Always verify the Dutch definition, file version, population, reference dates, variable availability and linking conditions in the original CBS documentation. A dataset's coverage period does not establish the availability of every variable. CBS decides access and applicable output requirements for each project.

The **map-only** planner runs in the browser. **AI planning and tutor requests** send the entered text and matching public documentation to OpenAI. Leave out personal, confidential or restricted information. See the site's [privacy and contact notice](https://www.cbsguru.org/privacy.html).

## What is in this repository?

**The live website is newer than the code currently published here.** This repository contains the earlier Streamlit prototype and its research pipeline. The current website implementation—including its hybrid planner, dataset graphs and translation-feedback service—is not yet included.

| Path | Contents |
| --- | --- |
| [`app/`](app/) | Earlier Streamlit interface; the conference deployment directs visitors to the permanent website |
| [`src/`](src/) | Python scraping, extraction, catalog-building and retrieval code from the prototype |
| [`data/raw_links/`](data/raw_links/) | Public documentation source links |
| [`notebooks/`](notebooks/) | Exploratory work on collecting documentation |
| [`docs/`](docs/) | Live demo walkthrough and historical prototype architecture and design notes |

For the current application, use **[www.cbsguru.org](https://www.cbsguru.org/)**. For reproducing the earlier Python prototype, see **[Legacy Streamlit setup](docs/legacy-streamlit.md)**. Raw PDFs, credentials and private runtime data are excluded from Git.

## Authors and presentation

Fernando A N Santos · Tommaso Giommoni · Wout Merbis · Tuan Phan · Clelia de Mulatier · Lourens Waldorp · Han van der Maas · Frank Pijpers · Mike Lees

**CBS Guru: A Retrieval-Augmented Assistant for Discovering CBS Microdata Variables in Computational Social Science** — [ODISSEI Conference 2026 submission](https://virtual.oxfordabstracts.com/event/77642/submission/66), 24 November 2026.

## Feedback and contributions

For a translation, use **Check this translation** on the relevant dataset page so the feedback stays attached to the exact passage and version. Suggestions are reviewed before any wording is changed.

For software problems, missing features or research examples that the pilot handles poorly, [open a GitHub issue](https://github.com/fnobregasantos/cbs-guru/issues). Include the page, relevant dataset or variable identifier, and steps to reproduce the problem. GitHub issues are public: do not include confidential research material, personal information, credentials or CBS microdata.

Dutch-speaking reviewers, experienced CBS users and researchers trying the pilot on real projects are welcome to contribute feedback. The [About page](https://www.cbsguru.org/about.html) describes the translation approach and pilot status.
