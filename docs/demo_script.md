# Live pilot demonstration

This walkthrough uses the public pilot at **[www.cbsguru.org](https://www.cbsguru.org/)**. It reflects the release of 23 November 2026, presented at the ODISSEI Conference on 24 November 2026. The website source is held for a separate release; the code currently in this repository is the earlier Streamlit prototype.

## Open the website

Explain that CBS Guru helps researchers navigate public CBS documentation and identify candidate datasets and variables. It does not provide access to confidential microdata or approve a data request. Dutch identifiers remain unchanged, and the original CBS PDFs remain authoritative.

Show a [dataset page](https://www.cbsguru.org/datasets/gbapersoontab.html#var-gbageboortelandnl): the Dutch variable name, English explanation, code values and source page. Use the Dutch-original control to compare a passage with its source.

## Plan an income-inequality project

1. Open **[Plan my project](https://www.cbsguru.org/plan.html)**.
2. Under **Presentation example**, select **Income inequality**, then **Load the example**. The preset covers 2019–2024 and produces concept-map results without an AI request.
3. Show the focused shortlist and **Why these items come first**. Explain that the ordering follows matching and selection rules; it is not a statistical confidence score.
4. Compare standardised disposable household income (`INHGESTINKH`, `INHATAB`) with household wealth (`VEHW1000VERH`, `VEHTAB`). Point out the distinction between income over a period and wealth at 1 January.
5. Scroll to **How the datasets could connect**. Select a dataset or an edge to inspect its linking keys, documentation and date checks.
6. Point out the person-to-household bridge with missing documentation. Candidate routes and required keys do not establish a successful join. Use every component of a composite key and align reference dates, file editions and geographic classifications.

Optionally click **Map + AI plan** to request an interpretation of the abstract and documentation. The concept-map results remain available alongside the AI explanation. This sends the abstract and relevant public documentation to OpenAI; use only non-confidential text. A live answer depends on service availability and the pilot's request limits.

## Ask the tutor

Open the **[Tutor](https://www.cbsguru.org/tutor.html)** for a focused documentation question, such as the difference between household income and personal earnings. Show the explanation, limitations and source links. Catalog checks reduce invented identifiers but do not establish that a real variable is suitable for a particular research question.

## Check one translation

On a dataset page, choose **Check this translation** and select a passage. Compare the Dutch and English text, then show the available choices: confirm, suggest a correction or mark uncertainty. Submit feedback only if you actually reviewed the passage.

Explain that feedback applies to the selected passage and version. Dutch proficiency is self-declared; submission counts are not verified independent reviewers or whole-page approval. Suggested corrections are moderated before a later website update.

## Invite questions and feedback

Ask attendees to try a research question, review a familiar passage or report a software issue. Use the website's passage feedback for translation checks and [GitHub issues](https://github.com/fnobregasantos/cbs-guru/issues) for software problems. Leave out confidential abstracts, personal data and CBS microdata.
