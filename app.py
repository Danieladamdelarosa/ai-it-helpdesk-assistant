import json

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from helpdesk_core import HelpdeskEngine, analyze_bulk_records

load_dotenv()
engine = HelpdeskEngine()

# -------------------- UI --------------------
st.set_page_config(page_title="AI IT Helpdesk Assistant", page_icon="💬", layout="centered")
st.title("💬 AI IT Helpdesk Assistant")
st.caption("LLM mode is **{}**".format("ON" if engine.use_llm else "OFF (rule-based)"))

tab_single, tab_bulk = st.tabs(["Single Ticket", "Bulk from CSV"])

with tab_single:
    subject = st.text_input("Subject", placeholder="Wi‑Fi not connecting after update")
    body = st.text_area("Description", height=180, placeholder="Explain what happened, any error codes, what you tried...")
    if st.button("Analyze Ticket", type="primary"):
        if not subject and not body:
            st.warning("Please enter a subject or description.")
        else:
            result = engine.analyze_ticket(subject, body)
            st.subheader("Result")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Category", result["category"].title())
            with col2:
                st.metric("Escalate?", "Yes" if result["escalate"] else "No")
            st.markdown("**Summary**")
            st.write(result["summary"])
            st.markdown("**Suggested Steps**")
            for i, step in enumerate(result["steps"], 1):
                st.write(f"{i}. {step}")

            export = {"subject": subject, "body": body, **result}
            st.download_button(
                "⬇️ Download JSON",
                data=json.dumps(export, indent=2),
                file_name="ticket_analysis.json",
                mime="application/json",
            )

with tab_bulk:
    st.write("Upload a CSV with columns: id, subject, body")
    file = st.file_uploader("Upload CSV", type=["csv"])
    if file:
        df = pd.read_csv(file)
        df.columns = [c.strip().lower() for c in df.columns]
        needed = {"subject", "body"}
        if not needed.issubset(set(df.columns)):
            st.error("CSV must include at least: subject, body (id optional).")
        else:
            rows = analyze_bulk_records(engine, df.to_dict("records"))
            out = pd.DataFrame(rows)
            st.dataframe(out, use_container_width=True)
            st.download_button(
                "⬇️ Download Results (CSV)",
                data=out.to_csv(index=False),
                file_name="bulk_ticket_analysis.csv",
                mime="text/csv",
            )

st.divider()
st.caption("Built for IT Management portfolios • MIT License")
