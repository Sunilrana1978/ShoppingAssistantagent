# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A multi-agent conversational shopping assistant built on **Google's Customer Experience Agent Studio (CX Agent Studio / CXAS)**, part of Gemini Enterprise for Customer Experience, managed via the `cxas-scrapi` CLI (`cxas`). This is *not* a standalone Python service you `run` locally in the usual sense — it's a declarative multi-agent app (JSON manifests + instruction prompts + Python tool/callback functions) that gets pushed to GCP and executed inside CX Agent Studio's runtime. Python code here also has a secondary purpose: it's unit-testable locally and doubles as the local simulation layer for `evaluations/run_evals.py`.

## Commands

Install (uses `uv`, Python >=3.10):
```bash
uv venv --python 3.10
uv pip install -e .
```

Lint the CXAS app structure (directory layout, manifests, prompts — target 0 errors):
```bash
uv run cxas lint
```

Validate manifests/schemas (`app.json`, agent JSONs, instruction files, `data/*.json`):
```bash
uv run python scripts/validate_schemas.py
```

Run the unit test suite (single file `tests/test_services.py`, `unittest`-based but pytest-compatible):
```bash
uv run python -m unittest discover tests/
# or
pytest tests/
# single test:
pytest tests/test_services.py::TestMultiAgentSystem::test_name -v
```

Run local multi-turn scenario evaluations (simulates the 9 `evaluations/tc_*` cases against the local tool/callback code, no GCP needed):
```bash
uv run python evaluations/run_evals.py
```

Push evaluations to a deployed CXAS app:
```bash
uv run cxas push-eval --app_name projects/ecom-cx-agent/locations/us/apps/shopping-assistant-app-dev \
    --file evaluations/tc_06_guest_user_flow/tc_06_guest_user_flow.json
uv run python scripts/push_all_evals.py projects/ecom-cx-agent/locations/us/apps/shopping-assistant-app-dev
```

Interactive local demo (simulated multi-agent conversation):
```bash
uv run python scripts/test_interactive_session.py
```

Deploy (runs pre-flight tests + schema validation, then `cxas push`):
```bash
uv run python scripts/build_app.py --env dev       # or staging / prod
```
CI (`.github/workflows/ci.yml`) runs `validate_schemas.py` → `pytest tests/` → `evaluations/run_evals.py` on every push/PR. CD (`.github/workflows/cd.yml`) deploys to staging on merge to `main`, and to prod on release tag, using GCP Workload Identity Federation (no static keys).

Microservice (Firestore-backed user profile/memory API, deployed separately to Cloud Run — see `microservice/deploy.sh`):
```bash
cd microservice && pip install -r requirements.txt && uvicorn main:app --reload
pytest microservice/test_main.py
```

## Architecture

**Three-agent router topology**, declared in `app.json` (`rootAgent: RootAgent`) and wired in `agents/*/*.json` manifests:
- `RootAgent` — supervisor; detects intent and hands off to a child agent (`childAgents: [ShoppingAssistant, FeedbackAgent]`). Owns the `end_session` client tool.
- `ShoppingAssistant` — greets by membership tier, searches the catalog, manages the cart. Tools: profile fetch, discount, search, add/remove cart, get cart.
- `FeedbackAgent` — collects 1-5 star ratings + comments via `submit_feedback`.

Each agent directory follows the same shape: `<Agent>.json` (manifest: instruction path, tools, child agents, callback registrations), `instruction.txt`/`instructions.xml` (the actual system prompt, structured with `<role>`/`<step>` tags), and callback subfolders (`before_agent_callbacks/`, `before_tool_callbacks/`, `after_tool_callbacks/`, `after_model_callbacks/`), each containing a numbered `..._01/python_code.py`. Callback registration order/wiring lives in the agent's `.json`, not inferred from directory names.

**Session state model.** All cross-turn/cross-agent state (`cart`, `user_id`, `user_name`, `membership_tier`, `discount_pct`, `long_term_memories`, etc.) is declared once, App-scoped, in `app.json`'s `variableDeclarations`, and shared transparently across agents during handoff. Two non-obvious platform rules govern mutating it from Python:
1. Returning `{"updatedVariables": {...}}` from a tool/callback is **not sufficient** to persist state in the CXAS Agent Engine runtime — code must also write through `context.state["key"] = value` (or `set_variable(...)`) directly.
2. `callback_context` can arrive as a plain `dict`, or an object exposing `.state`/`.variables`/`.session.state`, or CXAS runtime mapping types (`MapComposite`, `State`). Every callback in this repo reimplements the same `get_state()`/`set_state_var()` helper pair to normalize this — when adding a new callback, copy that pattern rather than assuming one shape.

**Tools must be self-contained.** CXAS executes `pythonFunction` tools (`tools/<name>/python_function/python_code.py`) in an isolated GCP sandbox that only has the stdlib. `from services...` or any other local module import causes a silent `400 Bad Request: No module named 'services'` at registration time, not at call time. Because of this, tool files duplicate embedded mock data/logic instead of importing `services/*`, and typically wrap `services.*` in a `try/except ImportError` fallback (works locally with real services for unit tests; falls back to inline logic on GCP). `fetch_user_profile` is the exception — it's an `openApiToolset` (`tools/fetch_user_profile/openapi_schema.json`) that calls the external Firestore microservice directly via HTTP rather than shipping Python.

**Service abstraction layer** (`services/interfaces.py`): `IUserService`, `IDiscountService`, `ICatalogService`, `ICartService`, `IFeedbackService`, currently implemented against mock JSON in `data/` (`mock_users.json`, `membership_discounts.json`, `mock_catalog.json`, `mock_feedback.json`). This layer exists for local unit tests / `run_evals.py` and as the local-fallback path inside tool files — it is not what runs when the tool executes inside the CXAS sandbox on GCP (see above). `gecx-config.toml` toggles `mock` vs. real backends per service for deployment profiles (`dev`/`staging`/`prod`), each mapped to a distinct `app_id`.

**Cross-session memory** (`microservice/`, FastAPI + Firestore, deployed to Cloud Run): exposes `/api/v1/users/{id}`, `/api/v1/users/{id}/memories`, `/api/v1/users/{id}/cart`, plus CXAS webhook endpoints `/api/v1/webhooks/before-agent` and `/api/v1/webhooks/after-tool`. `RootAgent`'s `before_agent_callback` resolves `user_id` and seeds defaults; the microservice webhook path (and/or the ADK/Vertex Memory Bank path referenced in `README.md`) is what actually recalls prior-session facts and cart state into `long_term_memories` for the current turn. When adding a new tool that should be remembered across sessions, persist through `firestore_service` here rather than only writing to session state, since session state doesn't survive a new session.

**Pricing is computed server-side**, never trusted from the model: `after_tool_callback` in `ShoppingAssistant` (and the microservice's after-tool webhook) recompute `subtotal` / `discount_amount` / `total` whenever `add_to_cart`, `remove_from_cart`, `get_cart`, or `get_discount` return, using `discount_pct` from state. Membership tiers map to fixed discounts: Gold 15%, Silver 10%, Bronze 5%, Guest 0% (`data/membership_discounts.json`).

**Guardrails and observability are declared in `app.json`**, not in code: blocklists (competitor brand redaction, PII/profanity regexes), a custom prompt-guard for jailbreak/injection screening, and ~7 natural-language behavioral rules, plus Cloud Logging + BigQuery export (`shopping_assistant_logs`) settings. When changing agent behavior around safety/compliance, check `app.json` guardrails before assuming it needs a code or prompt change.

## Conventions to follow

- Keep `tools/<name>/python_function/python_code.py` free of imports outside the stdlib (or guard non-stdlib imports with `try/except ImportError` and a working fallback) — this is a hard GCP registration constraint, not a style preference.
- New callbacks should reuse the existing `get_state`/`set_state_var` helper pattern (copy from e.g. `agents/ShoppingAssistant/after_tool_callbacks/after_tool_callbacks_01/python_code.py`) rather than assuming `callback_context` has a particular shape.
- Any tool response that should persist must both return `updatedVariables` *and* write through `context.state[...]` — the return value alone is not honored by the runtime.
- Run `uv run cxas lint` and `scripts/validate_schemas.py` before pushing agent/manifest changes — CI enforces both, and the deploy script (`build_app.py`) aborts the push if tests fail first.
