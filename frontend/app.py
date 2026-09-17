"""
app.py

Streamlit chat interface for Wayfinder (onboard-rag). Lets a user pick
their employee role (demonstrating role-based access control) and ask
onboarding questions, with grounded, cited answers streamed back via
the existing hybrid retrieval -> rerank -> generation pipeline.

Run with: streamlit run frontend/app.py
"""

import sys
import os

# Allow importing from src/ when running via `streamlit run frontend/app.py`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

from src.generation.generator import answer_query
from src.retrieval.hybrid_retriever import build_bm25_index

st.set_page_config(page_title="Onboard-RAG", page_icon=None, layout="centered")


@st.cache_resource(show_spinner="Setting up retrieval index...")
def warm_up():
    """Builds the BM25 index once per server process, not per interaction."""
    build_bm25_index()
    return True


warm_up()

st.title("Onboard-RAG")
st.caption("Ask onboarding questions across Techify's company documentation.")

ROLE_OPTIONS = {
    "No restriction (full corpus)": None,
    "Engineering": "engineering",
    "Sales": "sales",
    "Finance": "finance",
    "HR": "hr",
    "Marketing": "marketing",
    "Manager": "manager",
}

with st.sidebar:
    st.header("Settings")
    role_label = st.selectbox("Ask as role:", list(ROLE_OPTIONS.keys()))
    selected_role = ROLE_OPTIONS[role_label]
    st.markdown(
        "Selecting a role restricts retrieval to documents visible to that "
        "role, demonstrating the system's access control layer."
    )
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.markdown(f"- {source}")

user_input = st.chat_input("Ask a question about onboarding, policies, or processes...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving and generating an answer..."):
            result = answer_query(user_input, user_role=selected_role)

        st.markdown(result["answer"])

        if result["sources"]:
            with st.expander("Sources"):
                for source in result["sources"]:
                    st.markdown(f"- {source}")

        if result["top_score"] is not None:
            st.caption(f"Retrieval confidence score: {result['top_score']:.3f}")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
        }
    )