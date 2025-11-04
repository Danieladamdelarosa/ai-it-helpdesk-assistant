import os
import json
from typing import Dict, List

import streamlit as st
import pandas as pd

# --- Optional OpenAI (LLM mode) ---
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
use_llm = bool(OPENAI_KEY)
client = None
if use_llm:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
    except Exception:
        use_llm = False  # graceful fallback

# ---------- Simple rule-based fallback ----------
KEYWORDS = {
    "network": ["wifi", "wi-fi", "ethernet", "latency", "vpn", "proxy", "dns", "network"],
    "hardware": ["laptop", "keyboard", "mouse", "monitor", "battery", "charger", "power", "fan", "overheating"],
    "software": ["update", "install", "error", "bug", "crash", "app", "software", "driver", "patch"],
    "account": ["login", "locked", "password", "mfa", "2fa", "permission", "access", "account"],
}

SUGGESTIONS = {
    "network": [
        "Toggle Wi‑Fi adapter off/on",
        "Forget & re‑add the SSID",
        "Run ipconfig /flushdns (Windows) or dscacheutil -flushcache (macOS)",
        "Test with Ethernet or mobile hotspot",
        "Check VPN/Proxy settings"
    ],
    "hardware": [
        "Power cycle device",
        "Check cables/ports",
        "Run Device Manager/Drivers health check",
        "Run OEM diagnostics",
        "Open a replacement request if persistent"
    ],
    "software": [
        "Reboot and retry",
        "Clear cache/temp files",
        "Reinstall or rollback latest update",
        "Check logs for recent errors",
        "Open vendor ticket if reproducible"
    ],
    "account": [
        "Attempt self‑service password reset",
        "Verify MFA device/time sync",
        "Check group/role permissions",
        "Escalate to IAM if blocked",
        "Security check for suspicious activity"
    ],
}

def rule_based_classify(text: str) -> str:
    t = text.lower()
    scores = {k: 0 for k in KEYWORDS}
    for label, words in KEYWORDS.items():
        scores[label] = sum(1 for w in words if w in t)
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "software"

def rule_based_steps(category: str) -> List[str]:
    return SUGGESTIONS.get(category, SUGGESTIONS["software"])

def rule_based_escalation(text: str, category: str) -> bool:
    red_flags = ["data loss", "smoke", "burning", "security", "breach", "ransom", "admin down", "outage"]
    long_wait = any(p in text.lower() for p in red_flags)
    persistent = any(p in text.lower() for p in ["still", "again", "week", "days", "months"])
    return long_wait or category in ["hardware", "account"]

def llm_analyze(subject: str, body: str) -> Dict:
    content = f"Subject: {subject}\nBody: {body}\n"
    prompt = f'''
You are an IT helpdesk assistant. Classify the ticket into one of:
- network, hardware, software, account

Then propose 4-6 concrete next steps, and say whether to escalate (true/false) with a one-sentence reason.
Return STRICT JSON with keys: category, steps, escalate, summary.
Text to analyze:
\"\"\"\n{content}\n\"\"\"
JSON only:
'''
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        data["category"] = str(data.get("category", "software")).lower()
        data["steps"] = [str(s) for s in data.get("steps", [])][:8]
        data["escalate"] = bool(data.get("escalate", False))
        data["summary"] = str(data.get("summary", "")).strip()
        return data
    except Exception:
        category = rule_based_classify(subject + " " + body)
        return {
            "category": category,
            "steps": rule_based_steps(category),
            "escalate": rule_based_escalation(subject + " " + body, category),
            "summary": f"{category.title()} issue detected. Suggested standard troubleshooting steps applied.",
        }

def analyze_ticket(subject: str, body: str) -> Dict:
    if use_llm:
        return llm_analyze(subject, body)
    category = rule_based_classify(subject + " " + body)
    return {
        "category": category,
        "steps": rule_based_steps(category),
        "escalate": rule_based_escalation(subject + " " + body, category),
        "summary": f"{category.title()} issue. Applying baseline playbook. Escalate if unresolved.",
    }

# -------------------- UI --------------------
st.set_page_config(page_title="AI IT Helpdesk Assistant", page_icon="💬", layout="centered")
st.title("💬 AI IT Helpdesk Assistant")
st.caption("LLM mode is **{}**".format("ON" if use_llm else "OFF (rule-based)"))

tab_single, tab_bulk = st.tabs(["Single Ticket", "Bulk from CSV"])

with tab_single:
    subject = st.text_input("Subject", placeholder="Wi‑Fi not connecting after update")
    body = st.text_area("Description", height=180, placeholder="Explain what happened, any error codes, what you tried...")
    if st.button("Analyze Ticket", type="primary"):
        if not subject and not body:
            st.warning("Please enter a subject or description.")
        else:
            result = analyze_ticket(subject, body)
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
                mime="application/json"
            )

with tab_bulk:
    st.write("Upload a CSV with columns: id, subject, body")
    file = st.file_uploader("Upload CSV", type=["csv"])
    if file:
        df = pd.read_csv(file)
        # Normalize headers
        df.columns = [c.strip().lower() for c in df.columns]
        needed = {"subject", "body"}
        if not needed.issubset(set(df.columns)):
            st.error("CSV must include at least: subject, body (id optional).")
        else:
            rows = []
            for _, r in df.iterrows():
                res = analyze_ticket(str(r.get("subject", "")), str(r.get("body", "")))
                rows.append({
                    "id": r.get("id", ""),
                    "subject": r.get("subject", ""),
                    "category": res["category"],
                    "escalate": res["escalate"],
                    "summary": res["summary"],
                    "steps": " | ".join(res["steps"])
                })
            out = pd.DataFrame(rows)
            st.dataframe(out, use_container_width=True)
            st.download_button(
                "⬇️ Download Results (CSV)",
                data=out.to_csv(index=False),
                file_name="bulk_ticket_analysis.csv",
                mime="text/csv"
            )

st.divider()
st.caption("Built for IT Management portfolios • MIT License")
