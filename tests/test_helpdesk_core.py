from helpdesk_core import HelpdeskEngine, analyze_bulk_records


def test_rule_based_classifies_network_issue():
    engine = HelpdeskEngine(openai_api_key=None)
    result = engine.analyze_ticket("VPN issue", "wifi disconnect and dns errors")
    assert result["category"] == "network"
    assert len(result["steps"]) >= 4


def test_escalation_for_account_issue():
    engine = HelpdeskEngine(openai_api_key=None)
    result = engine.analyze_ticket("Account locked", "cannot login with mfa")
    assert result["category"] == "account"
    assert result["escalate"] is True


def test_llm_failure_falls_back_to_rules(monkeypatch):
    engine = HelpdeskEngine(openai_api_key=None)
    engine.use_llm = True

    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated llm failure")

    monkeypatch.setattr(engine, "_llm_analyze", boom)

    result = engine.analyze_ticket("Laptop overheating", "fan noise for days")
    assert result["category"] == "hardware"
    assert result["escalate"] is True


def test_bulk_records_shape():
    engine = HelpdeskEngine(openai_api_key=None)
    rows = analyze_bulk_records(
        engine,
        [
            {"id": 1, "subject": "wifi down", "body": "vpn and dns issue"},
            {"id": 2, "subject": "password reset", "body": "account locked again"},
        ],
    )

    assert len(rows) == 2
    assert set(rows[0].keys()) == {"id", "subject", "category", "escalate", "summary", "steps"}
