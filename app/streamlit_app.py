"""Streamlit app for the CBS Guru prototype."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guru_engine import ask_cbs_guru  # noqa: E402


CATALOG_PATH = ROOT / "data/processed/variables_catalog.csv"
DIEP_LOGO_URL = "https://static.wixstatic.com/media/5f1c7a_33082679ca504f8b977c4e98e8deb8e7~mv2.png/v1/fill/w_92,h_85,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/5f1c7a_33082679ca504f8b977c4e98e8deb8e7~mv2.png"
UVA_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/University_of_Amsterdam_logo.svg/960px-University_of_Amsterdam_logo.svg.png"
RPA_PSI_URL = "https://www.d-iep.org/rpapsi"

SUGGESTED_QUESTIONS = [
    "Which CBS variables can help study residential segregation, migration background, and income inequality in Amsterdam neighborhoods?",
    "Which CBS variables are useful for studying income inequality between households?",
    "Which CBS variables can help study school segregation or educational inequality?",
    "Which variables capture migration background and neighborhood composition?",
    "Which CBS documentation files are relevant for employment precarity?",
]


def main() -> None:
    load_dotenv(ROOT / ".env")
    st.set_page_config(page_title="CBS Guru", layout="wide")
    if not password_gate():
        return

    st.markdown(
        """
        <style>
        .block-container { max-width: 1100px; padding-top: 2rem; }
        .stButton button { width: 100%; text-align: left; border-radius: 6px; }
        textarea { border-radius: 6px !important; }
        .brand-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            padding: 16px 0 8px 0;
            border-bottom: 1px solid #e6e8ec;
            margin-bottom: 18px;
        }
        .brand-left {
            display: flex;
            align-items: center;
            gap: 16px;
            min-width: 0;
        }
        .diep-logo {
            width: 58px;
            height: 58px;
            object-fit: contain;
            border-radius: 6px;
            background: #0b0b0b;
        }
        .uva-logo {
            width: 210px;
            max-width: 28vw;
            height: auto;
            object-fit: contain;
        }
        .brand-kicker {
            color: #5b6472;
            font-size: 0.84rem;
            margin-bottom: 2px;
        }
        .brand-title {
            color: #101828;
            font-size: 1.45rem;
            font-weight: 700;
            line-height: 1.2;
        }
        .brand-subtitle {
            color: #344054;
            font-size: 0.92rem;
            line-height: 1.35;
            margin-top: 4px;
        }
        .brand-subtitle a {
            color: #0055a6;
            text-decoration: none;
            font-weight: 600;
        }
        .sponsor-note {
            background: #f7f9fc;
            border: 1px solid #e6e8ec;
            border-radius: 8px;
            padding: 12px 14px;
            color: #344054;
            margin-bottom: 18px;
        }
        @media (max-width: 720px) {
            .brand-header {
                align-items: flex-start;
                flex-direction: column;
            }
            .uva-logo {
                width: 180px;
                max-width: 70vw;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.subheader("Status")
        st.write(f"API key loaded: {'yes' if bool(os.environ.get('OPENAI_API_KEY')) else 'no'}")
        st.write(
            "Vector store ID loaded: "
            f"{'yes' if bool(os.environ.get('OPENAI_VECTOR_STORE_ID')) else 'no'}"
        )
        st.write(f"variables_catalog.csv found: {'yes' if CATALOG_PATH.exists() else 'no'}")
        st.write("Prototype mode: file_search over uploaded CBS PDFs")

    st.markdown(
        f"""
        <div class="brand-header">
            <div class="brand-left">
                <img class="diep-logo" src="{DIEP_LOGO_URL}" alt="DIEP logo">
                <div>
                    <div class="brand-kicker">DIEP · University of Amsterdam</div>
                    <div class="brand-title">CBS Guru</div>
                    <div class="brand-subtitle">
                        A prototype developed within the Research Priority Area
                        <a href="{RPA_PSI_URL}" target="_blank">Emergent Phenomena in Society</a>:
                        Polarization, Segregation and Inequality.
                    </div>
                </div>
            </div>
            <img class="uva-logo" src="{UVA_LOGO_URL}" alt="University of Amsterdam logo">
        </div>
        <div class="sponsor-note">
            This prototype is part of the RPA PSI project at the University of Amsterdam and acknowledges UvA support for the research priority area.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.warning(
        "CBS Guru is a prototype. It helps identify candidate variables in public CBS "
        "documentation. It does not provide access to confidential microdata. Always "
        "verify variables in the original CBS documentation."
    )

    st.markdown("#### Suggested demo questions")
    cols = st.columns(2)
    for index, question in enumerate(SUGGESTED_QUESTIONS):
        with cols[index % 2]:
            if st.button(question, key=f"suggested_{index}"):
                st.session_state["question"] = question

    question = st.text_area(
        "Question",
        value=st.session_state.get("question", SUGGESTED_QUESTIONS[0]),
        height=110,
    )

    if st.button("Ask CBS Guru", type="primary"):
        with st.spinner("Searching uploaded CBS documentation..."):
            answer = ask_cbs_guru(question)
        st.markdown(answer)


def password_gate() -> bool:
    expected_password = get_secret("APP_PASSWORD")
    if not expected_password:
        return True

    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;gap:24px;margin:18px 0 22px 0;padding-bottom:16px;border-bottom:1px solid #e6e8ec;">
            <div style="display:flex;align-items:center;gap:16px;">
                <img src="{DIEP_LOGO_URL}" alt="DIEP logo" style="width:58px;height:58px;object-fit:contain;border-radius:6px;background:#0b0b0b;">
                <div>
                    <div style="color:#5b6472;font-size:0.84rem;margin-bottom:2px;">DIEP · University of Amsterdam</div>
                    <div style="color:#101828;font-size:1.45rem;font-weight:700;line-height:1.2;">CBS Guru</div>
                    <div style="color:#344054;font-size:0.92rem;line-height:1.35;margin-top:4px;">Prototype access for the RPA Emergent Phenomena in Society project.</div>
                </div>
            </div>
            <img src="{UVA_LOGO_URL}" alt="University of Amsterdam logo" style="width:210px;max-width:28vw;height:auto;object-fit:contain;">
        </div>
        """,
        unsafe_allow_html=True,
    )
    password = st.text_input("Password", type="password")
    if st.button("Enter", type="primary"):
        if password == expected_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


def get_secret(name: str) -> str:
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.environ.get(name, "")


if __name__ == "__main__":
    main()
