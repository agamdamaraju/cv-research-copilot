import streamlit as st
import requests, json

# BACKEND = st.secrets.get("backend", "http://localhost:8000")
BACKEND = "http://localhost:8000"

st.set_page_config(page_title="CV Research Copilot", layout="wide")
st.title("🔬 CV Research Copilot")

with st.sidebar:
    st.markdown("**Backend**: " + BACKEND)
    st.caption("Upload a PDF, click Ingest, then ask questions or extract JSON.")

if "doc_id" not in st.session_state:
    st.session_state.doc_id = None

st.header("1) Upload PDF & Ingest")
uploaded = st.file_uploader("Select a CV paper PDF", type=["pdf"])
if uploaded and st.button("Ingest"):
    files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
    r = requests.post(f"{BACKEND}/ingest/", files=files, timeout=600)
    if r.ok:
        payload = r.json()
        st.session_state.doc_id = payload["doc_id"]
        st.success(f"Ingested. doc_id={payload['doc_id']} pages={payload['pages']}")
    else:
        st.error(r.text)

st.header("2) Ask Questions (with citations)")
col1, col2 = st.columns([2,1])
with col1:
    q = st.text_input("Question", placeholder="e.g., What is the main method and its loss functions?")
    if st.button("Ask", use_container_width=True):
        if not st.session_state.doc_id:
            st.warning("Ingest a PDF first.")
        else:
            r = requests.post(f"{BACKEND}/ask/", json={"doc_id": st.session_state.doc_id, "question": q})
            if r.ok:
                st.markdown(r.json()["answer"])  # contains [p:##]
            else:
                st.error(r.text)
with col2:
    st.info("Answers are constrained to retrieved pages and include [p:##] page markers.")

st.header("3) Extract Structured JSON")
if st.button("Extract JSON", use_container_width=True):
    if not st.session_state.doc_id:
        st.warning("Ingest a PDF first.")
    else:
        r = requests.post(f"{BACKEND}/extract/", json={"doc_id": st.session_state.doc_id})
        if r.ok:
            data = r.json()["data"]
            st.code(json.dumps(data, indent=2), language="json")
            st.download_button("Download paper.json", data=json.dumps(data, indent=2), file_name="paper.json")
        else:
            st.error(r.text)
