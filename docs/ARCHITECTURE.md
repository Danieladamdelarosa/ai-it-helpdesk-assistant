# Architecture Overview

## Components
- **`app.py`**: Streamlit UI layer for single-ticket and bulk CSV analysis.
- **`helpdesk_core.py`**: Core domain logic (`HelpdeskEngine`) and bulk transformation helper.
- **`tests/test_helpdesk_core.py`**: Unit tests for classification, escalation, fallback, and bulk output shape.

## Request flow
1. User enters ticket subject/body (or uploads CSV).
2. UI passes input into `HelpdeskEngine.analyze_ticket`.
3. Engine normalizes text and computes rule-based baseline category.
4. If `OPENAI_API_KEY` is configured, engine attempts structured LLM analysis.
5. On any LLM parse/API failure, engine falls back to deterministic rule-based output.
6. UI renders category, escalation recommendation, summary, and steps.

## Reliability decisions
- **Fail-safe behavior**: LLM failures never block output; fallback path is always available.
- **Bounded normalization**: Input text is trimmed and whitespace-normalized to limit prompt bloat.
- **Schema sanitation**: LLM result is validated/normalized before returning to UI.

## MVP extension points
- Replace static keyword/rule config with a managed datastore.
- Add persistent ticket history and analytics.
- Add auth, audit logs, and rate limits for production hardening.
