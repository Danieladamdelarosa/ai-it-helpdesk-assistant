import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

KEYWORDS = {
    "network": ["wifi", "wi-fi", "ethernet", "latency", "vpn", "proxy", "dns", "network"],
    "hardware": [
        "laptop",
        "keyboard",
        "mouse",
        "monitor",
        "battery",
        "charger",
        "power",
        "fan",
        "overheating",
    ],
    "software": ["update", "install", "error", "bug", "crash", "app", "software", "driver", "patch"],
    "account": ["login", "locked", "password", "mfa", "2fa", "permission", "access", "account"],
}

SUGGESTIONS = {
    "network": [
        "Toggle Wi‑Fi adapter off/on",
        "Forget & re‑add the SSID",
        "Run ipconfig /flushdns (Windows) or dscacheutil -flushcache (macOS)",
        "Test with Ethernet or mobile hotspot",
        "Check VPN/Proxy settings",
    ],
    "hardware": [
        "Power cycle device",
        "Check cables/ports",
        "Run Device Manager/Drivers health check",
        "Run OEM diagnostics",
        "Open a replacement request if persistent",
    ],
    "software": [
        "Reboot and retry",
        "Clear cache/temp files",
        "Reinstall or rollback latest update",
        "Check logs for recent errors",
        "Open vendor ticket if reproducible",
    ],
    "account": [
        "Attempt self‑service password reset",
        "Verify MFA device/time sync",
        "Check group/role permissions",
        "Escalate to IAM if blocked",
        "Security check for suspicious activity",
    ],
}

VALID_CATEGORIES = set(KEYWORDS.keys())


@dataclass
class HelpdeskEngine:
    openai_api_key: Optional[str] = None
    client: Optional[object] = None
    use_llm: bool = False

    def __post_init__(self) -> None:
        key = self.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            return

        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=key)
            self.use_llm = True
        except Exception:
            self.client = None
            self.use_llm = False

    @staticmethod
    def _normalize_text(text: str, max_chars: int = 4000) -> str:
        return " ".join((text or "").split())[:max_chars]

    @staticmethod
    def _rule_based_classify(text: str) -> str:
        t = text.lower()
        scores = {k: sum(1 for w in words if w in t) for k, words in KEYWORDS.items()}
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "software"

    @staticmethod
    def _rule_based_steps(category: str) -> List[str]:
        return SUGGESTIONS.get(category, SUGGESTIONS["software"])

    @staticmethod
    def _rule_based_escalation(text: str, category: str) -> bool:
        red_flags = ["data loss", "smoke", "burning", "security", "breach", "ransom", "admin down", "outage"]
        long_wait = any(p in text.lower() for p in red_flags)
        persistent = any(p in text.lower() for p in ["still", "again", "week", "days", "months"])
        return long_wait or persistent or category in ["hardware", "account"]

    @staticmethod
    def _sanitize_result(data: Dict, fallback_category: str) -> Dict:
        category = str(data.get("category", fallback_category)).lower().strip()
        if category not in VALID_CATEGORIES:
            category = fallback_category

        steps = [str(s).strip() for s in data.get("steps", []) if str(s).strip()][:8]
        if not steps:
            steps = SUGGESTIONS.get(category, SUGGESTIONS["software"])

        return {
            "category": category,
            "steps": steps,
            "escalate": bool(data.get("escalate", False)),
            "summary": str(data.get("summary", "")).strip()
            or f"{category.title()} issue. Applying baseline playbook.",
        }

    def _llm_analyze(self, subject: str, body: str) -> Dict:
        if not self.client:
            raise RuntimeError("LLM client unavailable")

        content = f"Subject: {subject}\nBody: {body}\n"
        prompt = (
            "You are an IT helpdesk assistant. Classify this ticket as network, hardware, software, or account. "
            "Provide 4-6 concrete next steps, whether to escalate as a boolean, and a short summary."
        )

        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {"role": "system", "content": "Return JSON with keys: category, steps, escalate, summary."},
                {"role": "user", "content": f"{prompt}\n\n{content}"},
            ],
        )
        raw = (resp.choices[0].message.content or "").strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        fallback = self._rule_based_classify(f"{subject} {body}")
        return self._sanitize_result(parsed, fallback)

    def analyze_ticket(self, subject: str, body: str) -> Dict:
        subject_norm = self._normalize_text(subject)
        body_norm = self._normalize_text(body)
        combined = f"{subject_norm} {body_norm}".strip()
        category = self._rule_based_classify(combined)

        if self.use_llm:
            try:
                return self._llm_analyze(subject_norm, body_norm)
            except Exception:
                pass

        return {
            "category": category,
            "steps": self._rule_based_steps(category),
            "escalate": self._rule_based_escalation(combined, category),
            "summary": f"{category.title()} issue. Applying baseline playbook. Escalate if unresolved.",
        }


def analyze_bulk_records(engine: HelpdeskEngine, records: List[Dict]) -> List[Dict]:
    results = []
    for record in records:
        subject = str(record.get("subject", ""))
        body = str(record.get("body", ""))
        analysis = engine.analyze_ticket(subject, body)
        results.append(
            {
                "id": record.get("id", ""),
                "subject": subject,
                "category": analysis["category"],
                "escalate": analysis["escalate"],
                "summary": analysis["summary"],
                "steps": " | ".join(analysis["steps"]),
            }
        )
    return results
