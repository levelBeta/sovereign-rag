"""Streamlit UI for Sovereign RAG. ALL DATA IS SYNTHETIC.
Shows role, redacted query, retrieved and filtered chunks, cited answer or refusal,
audit chain status and the sovereignty result."""
import os
import streamlit as st
import agent
import audit

UI_AUDIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_ui.jsonl")
MODELS = ["qwen2.5:3b", "qwen2.5:7b", "llama3.2:3b"]

st.set_page_config(page_title="Sovereign RAG", layout="wide")


@st.cache_resource
def load():
    return agent.build()


col, chunks = load()
st.title("Sovereign RAG")
st.caption("Local, role-aware answers with verified citations. All data is synthetic.")
role = st.sidebar.selectbox("Role", ["analyst", "manager", "ciso"])
model = st.sidebar.selectbox("Model", MODELS)
st.sidebar.write("Audit log:", os.path.basename(UI_AUDIT))
question = st.text_input("Ask a question about the policy documents")

if question:
    with st.spinner("Running locally..."):
        out = agent.analyse(col, chunks, question, role, model=model, audit_path=UI_AUDIT)
    res = out["result"]
    st.subheader("1. Redacted query")
    st.code(out["redacted_query"])
    st.write("PII found and redacted (counts only):", out["pii_counts"] or "none")
    st.subheader("2. Retrieved passages for role: " + role)
    st.write("Best vector distance:", out["best_distance"], "(refused above %s)" % agent.MAX_DISTANCE)
    for r in out["retrieval"]["results"]:
        st.write("**%s** (rrf %s, distance %s): %s" % (r["chunk_id"], r["rrf"], r["distance"], r["text"]))
    filt = out["retrieval"]["filtered_out"]
    st.write("Filtered out by the role re-check:", [d["chunk_id"] for d in filt] if filt else "none")
    st.subheader("3. Answer")
    if res["status"] == "answered":
        st.success(res["answer"])
        for c in res["citations"]:
            st.write("Cited **%s**: \"%s\"" % (c["chunk_id"], c["quote"]))
        st.caption("Code verified each citation is retrieved, permitted and verbatim, and each number "
                   "appears in the cited text. It cannot verify the answer reasons correctly from it.")
    else:
        st.warning("Refused: %s" % res["reason"])
        if res["details"]:
            st.write("Details:", res["details"])
    st.subheader("4. Governance")
    v = audit.verify(UI_AUDIT)
    st.write("Audit chain:", "intact" if v["ok"] else "BROKEN at line %s" % v["first_bad"],
             "(%d entries)" % v["entries"])
    sov = out["sovereignty"]
    st.write(sov["claim"])
    st.caption(sov["scope"])
