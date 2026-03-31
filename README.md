# AI IT Helpdesk Assistant (MVP)

A lightweight Streamlit app that triages IT helpdesk tickets using a rule-based engine with optional OpenAI-powered enrichment.

## What this MVP does
- Classifies tickets into `network`, `hardware`, `software`, or `account`.
- Suggests actionable troubleshooting steps.
- Recommends escalation when risk/persistence indicators are present.
- Supports single-ticket and bulk CSV workflows.
- Runs with or without an OpenAI API key.

## Quickstart
1. Create and activate a virtual environment.
2. Install dependencies.
3. Copy `.env.example` to `.env`.
4. Launch the app.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Open the local URL shown by Streamlit (usually `http://localhost:8501`).

## Environment variables
- `OPENAI_API_KEY` (optional): enables LLM mode.

If no API key is present (or OpenAI initialization fails), the app automatically uses the rule-based engine.

## CSV input format
CSV must contain:
- `subject`
- `body`

Optional:
- `id`

## Run tests
```bash
pytest -q
```

## Architecture
See `docs/ARCHITECTURE.md` for a concise component map and design rationale.

## Known production risks and next steps
1. **Security**: No auth/RBAC yet; deploy behind SSO or API gateway before multi-user production.
2. **Performance**: Bulk processing is synchronous in-process; add queue workers for large datasets.
3. **Maintainability**: Rule sets are static in code; move to versioned config or admin-managed datastore.
