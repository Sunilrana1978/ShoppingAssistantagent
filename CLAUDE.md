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
`cxas-scrapi` is pinned to `==1.7.0` in `pyproject.toml`/`requirements.txt` — **do not bump it** without checking first. `1.8.0` shipped a docstring-parsing bug in its `V001`/`V004` schema-validation rules that misflags genuinely `Optional` proto fields as missing/required whenever their description text happens to contain the word "required" as prose (e.g. `OpenApiToolset.api_authentication`). CI installs via `pip install -e .`, so it always uses this pin too — don't let CI's install step drift back to an unpinned `pip install cxas-scrapi`.

Lint the CXAS app structure (directory layout, manifests, prompts, proto schema conformance — target 0 errors):
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

Run local multi-turn scenario evaluations (simulates the 9 `evaluations/tc_*` cases against the local tool/callback code, no GCP needed — but never exercises `RootAgent`'s routing, see below):
```bash
uv run python evaluations/run_evals.py
```

Live routing smoke test against a **deployed** app (needs GCP creds, burns model quota, not in CI — run manually after touching any `agents/*/instruction.txt` or `agents/*/*.json`):
```bash
uv run python scripts/smoke_test_routing.py --env dev
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

Deploy the CXAS app (runs pre-flight tests + schema validation, `cxas push`, then re-applies agent↔toolset bindings — see below):
```bash
uv run python scripts/build_app.py --env dev       # or staging / prod
```
CI (`.github/workflows/ci.yml`) runs `validate_schemas.py` → `cxas lint` → `pytest tests/` → `evaluations/run_evals.py` on every push/PR. CD (`.github/workflows/cd.yml`) deploys to staging on merge to `main`, and to prod on release tag, using GCP Workload Identity Federation (no static keys).

Microservice (Firestore-backed user-memory API backing the OpenAPI toolsets, deployed separately to Cloud Run):
```bash
cd microservice && pip install -r requirements.txt && uvicorn main:app --reload
pytest microservice/test_main.py
bash microservice/deploy.sh    # deploys shopping-user-service to Cloud Run — must be redeployed manually, it is not part of build_app.py
```

## Architecture

**Three-agent router topology**, declared in `app.json` (`rootAgent: RootAgent`) and wired in `agents/*/*.json` manifests:
- `RootAgent` — pure supervisor; detects intent and transfers to a child agent (`childAgents: [ShoppingAssistant, FeedbackAgent]`). Owns the `end_session` client tool. **It never answers the user directly** — even a bare "hello" transfers to `ShoppingAssistant` rather than `RootAgent` replying itself, because `RootAgent` has no `fetch_user_profile` binding and never will (see "Persistent memory" below for why not). If you find `RootAgent`'s instruction answering a message inline instead of transferring, that's very likely a bug — `evaluations/run_evals.py` won't catch it since it never exercises `RootAgent`'s routing; use `scripts/smoke_test_routing.py` against a live deploy instead.
- `ShoppingAssistant` — greets by membership tier, searches the catalog, manages the cart, reads/writes user memory & preferences. `tools`: `get_discount`, `search_catalog`, `add_to_cart`, `get_cart`, `remove_from_cart`, `end_session`, `show_product_carousel`. `toolsets`: `fetch_user_profile`, `add_user_memory`, `update_user_preferences`.
- `FeedbackAgent` — collects 1-5 star ratings + comments via `submit_feedback`. `toolsets`: `add_user_memory`.

Each agent directory follows the same shape: `<Agent>.json` (manifest: instruction path, `tools`, `toolsets`, child agents, callback registrations), `instruction.txt` (the actual system prompt, structured with `<role>`/`<persona>`/`<context>`/`<taskflow>`/`<step>`/`<guardrails>` tags — **not** `<state_visibility>` or any tag starting with `<state`, `<Context>` (capitalized), `<Role>`, `<Persona>`, etc.: `cxas lint`'s `I015` rule bans the legacy CamelCase/state-machine tag set), and callback subfolders (`before_agent_callbacks/`, `before_tool_callbacks/`, `after_tool_callbacks/` — `after_model_callbacks/` is a platform-supported type but unused in this repo, see "Widget tools" below for why), each containing a numbered `..._01/python_code.py`. Callback registration order/wiring lives in the agent's `.json`, not inferred from directory names.

**Session state model.** All cross-turn/cross-agent state (`cart`, `user_id`, `user_name`, `membership_tier`, `discount_pct`, `long_term_memories`, `preferences`, etc.) is declared once, App-scoped, in `app.json`'s `variableDeclarations`, and shared transparently across agents during handoff. Three non-obvious platform rules govern mutating it from Python:
1. Returning `{"updatedVariables": {...}}` from a tool/callback is **not sufficient** to persist state in the CXAS Agent Engine runtime — code must also write through `context.state["key"] = value` (or `set_variable(...)`) directly.
2. `callback_context` can arrive as a plain `dict`, or an object exposing `.state`/`.variables`/`.session.state`, or CXAS runtime mapping types (`MapComposite`, `State`). Every callback in this repo reimplements the same `get_state()`/`set_state_var()` helper pair to normalize this — when adding a new callback, copy that pattern rather than assuming one shape.
3. A tool/toolset's response fields don't automatically populate matching-named session variables just because the names line up — e.g. `fetch_user_profile` returning `memories`/`preferences` does nothing to `{long_term_memories}`/`{preferences}` unless a callback explicitly copies them across (see `agents/ShoppingAssistant/after_tool_callbacks/after_tool_callbacks_01/python_code.py`). This was a real bug found and fixed this project: `state_visibility` documented those variables as available, but nothing ever set them.

**pythonFunction tools run in a network-isolated sandbox — this is the single most important platform fact in this repo.** CXAS executes `pythonFunction` tools (`tools/<name>/python_function/python_code.py`) *and* callbacks in an isolated GCP sandbox with **zero outbound network access** (confirmed by direct testing — any `urllib`/`requests` call fails immediately with DNS-resolution or "network unreachable" errors, regardless of target host). Consequences:
- Tool/callback source files must be self-contained, stdlib-only. `from services...` or any other local module import causes a silent `400 Bad Request: No module named 'services'` at registration time. Tool files wrap `services.*` imports in `try/except ImportError` (works locally for unit tests; falls back to embedded mock data on GCP).
- **Any call to an external HTTP API must go through a CXAS OpenAPI toolset, never inline Python code.** This is why `fetch_user_profile`, `add_user_memory`, and `update_user_preferences` live under `toolsets/` (OpenAPI resources CXAS executes natively, outside the sandbox) rather than as `pythonFunction` tools that just call `requests.post(...)`. An earlier version of `add_to_cart`/`remove_from_cart` tried to sync the cart to Firestore via inline `urllib` calls — it silently no-opped on every single call while still returning `"status": "success"`. That code has been removed; cart state is now session-only.

**Tool vs. Toolset — easy to get wrong, platform doesn't clearly error on the wrong shape:**
- A **`Tool`** (`tools/<name>/`) has an `openApiTool` field (singular) for one HTTP operation.
- A **`Toolset`** (`toolsets/<name>/`, schema at `toolsets/<name>/open_api_toolset/open_api_schema.yaml`) has an `openApiToolset` field, can expose multiple operations. In practice, **pushing an OpenAPI-based config always creates a `Toolset` server-side**, regardless of which field name was used locally — so every OpenAPI tool in this repo lives under `toolsets/`.
- The model calls the compound name `{toolset_name}_{operationId}` (e.g. `fetch_user_profile_fetch_user_profile`) — that's what `instruction.txt`'s `{@TOOL: ...}` placeholders must reference, not the bare toolset name.
- Binding uses the agent manifest's separate `toolsets` array (`[{"toolset": "<name>", "toolIds": ["<operationId>"]}]`), **not** the `tools` array — a bare string there hard-fails the push with `Reference '<name>' of type 'ces.googleapis.com/Tool' not found`.
- `cxas push`'s bulk import creates/updates `Toolset` resources correctly but **silently drops each agent's `toolsets` binding**. `scripts/build_app.py` re-applies these after every push via a direct `update_agent` API call reading `toolsets` straight out of each `agents/*/*.json` — this is why deploys print "Reconciling agent toolset bindings". This step is generic; a new toolset needs no script changes.
- Request-body schema gotcha: a property typed as schemaless `{"type": "object"}` silently arrives as `{}` server-side — the OpenAPI executor only forwards fields it can resolve through explicit nested `properties`. A top-level array-of-strings field passes through fine without extra structure; it's specifically nested objects that need their full shape spelled out (see `toolsets/update_user_preferences/` for a worked example).

**Widget tools render rich UI (images, cards) — never try to do this via `after_model_callback` again.** An earlier version had `ShoppingAssistant`'s `after_model_callback` try to attach a custom `custom_payload`/`rich_widgets` field to the model response after `search_catalog` ran. It could never have worked: proven via live instrumentation that `after_model_callback`'s state view only reflects what was persisted *before* the current turn started, never `search_results`/`cart`/`discount_pct` set by tools called earlier in the same turn. That callback has been deleted entirely. The correct mechanism is `WidgetTool` — a oneof variant on the `Tool` resource itself (same family as `pythonFunction`/`openApiTool`), so it lives under `tools/<name>/<name>.json` like any other tool (no separate `widgets/` directory — one isn't in `cxas push`'s bundle, and files there would be silently dropped). The model calls it directly and the platform renders it, no callback/state involved at all. `tools/show_product_carousel/` uses the pre-built `PRODUCT_CAROUSEL` `widgetType`. `cxas-scrapi` has no scaffolding template for widgets yet — the reliable way to get a `widgetType`'s exact `parameters` schema is to build one once in Studio's Widgets panel, then `cxas pull <app> --target-dir <scratch-dir>` (never `--overwrite` straight onto the repo) and copy the generated JSON in.

**Service abstraction layer** (`services/interfaces.py`): `IUserService`, `IDiscountService`, `ICatalogService`, `ICartService`, `IFeedbackService`, implemented against mock JSON in `data/`. This layer exists for local unit tests / `run_evals.py` and as the local-fallback path inside tool files — it is not what runs when the tool executes inside the CXAS sandbox on GCP. `gecx-config.toml` toggles `mock` vs. real backends per service for deployment profiles (`dev`/`staging`/`prod`), each mapped to a distinct `app_id`.

**Persistent memory is two separate, deliberately session-independent channels, both backed by Firestore via the `shopping-user-service` Cloud Run microservice** (`microservice/`, FastAPI + `firestore_service.py`, `user_profiles` collection):
- **Free-text facts** (`memories: []`, via `add_user_memory`) — short narrative sentences for context that doesn't fit a fixed shape.
- **Structured preferences** (`preferences: {}`, via `update_user_preferences`) — `preferred_categories`/`preferred_sports`/`preferred_brands`/`shoe_size`/`apparel_size`/`equipment_size`/`price_max`, aligned to `search_catalog`'s own filter params so they double as default search filters. Merge semantics on write: list fields union+dedupe, scalars overwrite.
- **The live cart is never persisted to Firestore** — it's session-scoped only (`{cart}` in App-level state). Don't reintroduce cart-to-Firestore syncing; it was tried, found to be architecturally impossible from inside the sandbox (see above), and removed.
- `fetch_user_profile` reads both channels at session start (`ShoppingAssistant` only — deliberately not duplicated onto `RootAgent`, which would either double-fetch on every session or tax `FeedbackAgent`-only sessions with an unused Firestore round-trip).
- Writes are **explicit model-invoked tool calls**, never callback-driven (callbacks can't make the HTTP call — same sandbox constraint). Trigger points: `update_user_preferences` fires immediately on an explicit user statement ("I wear size 10"); both tools fire at session-close as a consolidated, inferred-signal fallback; `FeedbackAgent` writes a memory fact right after `submit_feedback` succeeds (the one deterministic, always-fires trigger).

**Pricing is computed server-side**, never trusted from the model: `after_tool_callback` in `ShoppingAssistant` recomputes `subtotal` / `discount_amount` / `total` whenever `add_to_cart`, `remove_from_cart`, `get_cart`, or `get_discount` return, using `discount_pct` from state. Membership tiers map to fixed discounts: Gold 15%, Silver 10%, Bronze 5%, Guest 0% (`data/membership_discounts.json`).

**Guardrails are first-class resources, not inline `app.json` config** — despite how that might read at a glance. `Guardrail` is its own CES proto resource type (like `Tool`/`Toolset`): each one is a separate `guardrails/<name>/<name>.json` file with one of `contentFilter` (blocklist/regex), `llmPromptSecurity` (jailbreak/injection detection), or `llmPolicy` (natural-language behavioral rule) set, plus an `action` (`generativeAnswer` or `respondImmediately`). `app.json`'s top-level `guardrails` array is just a list of these resource IDs by directory name — an earlier version tried embedding the guardrail definitions inline in `app.json`, which silently failed to push and got deleted rather than fixed, so **check that `guardrails/` actually contains a file for every ID listed in `app.json`'s `guardrails` array** before assuming this area works. Schema gotcha: `TriggerAction.RespondImmediately.responses` is `repeated {text, disabled}`, not `repeated string` — a bare string array fails lint with a cryptic "no field named 'F'" (the parser reads the string's first character as a field name).

## Conventions to follow

- Keep `tools/<name>/python_function/python_code.py` (and callbacks) free of imports outside the stdlib and free of any outbound network call — both are hard sandbox constraints, not style preferences. Anything that needs to reach an external API goes through a `toolsets/` OpenAPI resource instead.
- New callbacks should reuse the existing `get_state`/`set_state_var` helper pattern (copy from e.g. `agents/ShoppingAssistant/after_tool_callbacks/after_tool_callbacks_01/python_code.py`) rather than assuming `callback_context` has a particular shape.
- Any tool response that should persist must both return `updatedVariables` *and* write through `context.state[...]` — the return value alone is not honored by the runtime.
- When a toolset's response should populate a session variable, that mapping must be added explicitly in the relevant `after_tool_callback` — it does not happen automatically from matching field names.
- Run `uv run cxas lint` and `scripts/validate_schemas.py` before pushing agent/manifest/guardrail changes — CI enforces both, and the deploy script (`build_app.py`) aborts the push if tests fail first. After touching anything under `agents/*/instruction.txt` or `*.json`, also run `scripts/smoke_test_routing.py --env dev` — it's the only check that exercises `RootAgent`'s actual routing behavior.
