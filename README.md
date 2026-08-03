# Sporting Goods Multi-Agent Shopping & Feedback Assistant

A multi-agent conversational application for a sporting goods storefront (shoes, apparel, equipment) built on **Customer Experience Agent Studio (CX Agent Studio)** — part of **Gemini Enterprise for Customer Experience** — and managed programmatically using **`cxas-scrapi`** (`GoogleCloudPlatform/cxas-scrapi`).

---

## 🌟 Overview & Key Features

The application features a **Multi-Agent Router Architecture** driven by natural-language XML instructions, Python code tools, execution callbacks, dynamic session variables, and a pluggable service abstraction layer:

- **Root Router Agent (`RootAgent`)**: Central supervisor that detects customer intent and routes between shopping discovery and customer feedback.
- **Shopping Assistant (`ShoppingAssistant`)**: Greets members, surfaces membership-tier discounts, searches product catalogs based on natural-language queries, and manages session shopping carts.
- **Customer Feedback Agent (`FeedbackAgent`)**: Collects 1 to 5 star ratings and customer feedback comments, logging them into analytics.
- **App-level Guardrails**: Centrally manages security using Custom Prompt Guards (jailbreak/injection filters), deterministic Blocklists (PII, competitor brands, and profanity), and natural-language Rules across all agents.
- **Logging & Observability**: Configured Cloud Logging with 1-year retention and automatic BigQuery analytics export to analyze conversation flows, intent statistics, and user interactions.
- **Persistent User Memory (Firestore)**: A Cloud Run microservice backed by Firestore stores two kinds of durable knowledge per user — free-text interaction facts (`add_user_memory`) and structured shopping preferences (`update_user_preferences`: categories, sports, brands, sizes, budget) — both recalled via `fetch_user_profile` so future sessions can give better recommendations. The live shopping cart itself stays session-scoped and is never persisted.
- **Membership Discount Engine**: Automatically applies member discounts (**Gold: 15%**, **Silver: 10%**, **Bronze: 5%**, **Guest: 0%**) to product prices and cart totals.
- **Server-Side Pricing Math**: Calculates exact float arithmetic for cart subtotals, discount amounts, and grand totals server-side via callback functions.
- **Rich Response Widgets**: `ShoppingAssistant` calls a native CXAS `WidgetTool` (`tools/show_product_carousel/`) directly after `search_catalog`, rendering results as an image-bearing product carousel — a first-class platform tool the model invokes itself, not a callback formatting a custom payload.
- **Service Abstraction Layer**: Data access is isolated behind `IUserService`, `IDiscountService`, `ICatalogService`, `ICartService`, and `IFeedbackService` interfaces — currently backed by mock JSON files, ready to swap for real REST/OpenAPI backends.
- **CI/CD & Environment Promotion**: Fully configured GitHub Actions workflows for continuous integration quality gates (`.github/workflows/ci.yml`) and multi-environment deployment (`.github/workflows/cd.yml`).
- **Web Widget Embed (`web/`)**: A standalone static test page embedding Google's `chat-messenger` SDK against the deployed dev app, self-authenticating via the CXAS token broker — servable locally with zero dependencies.

---

## 🏗️ Architecture Diagram

```mermaid
flowchart LR
    subgraph Client["1. Client Layer"]
        Widget["Web Chat Widget / Channel"]
    end

    subgraph Router["2. Router Agent Layer"]
        Root["RootAgent (Supervisor)\nIntent Detection & Routing\n(always transfers —\nnever answers directly)"]
    end

    subgraph DomainAgents["3. Specialized Domain Agents"]
        ShopAgent["ShoppingAssistant\n(Discovery, Cart,\nPersonalization)"]
        FeedAgent["FeedbackAgent\n(Rating & Feedback)"]
    end

    subgraph Sandbox["4. pythonFunction Tools & Callbacks\n(sandboxed — zero network egress)"]
        PyTools["get_discount, search_catalog,\nadd/remove/get_cart, submit_feedback"]
        Callbacks["before_agent / before_tool /\nafter_tool callbacks"]
        MockData[("JSON Mock Catalog &\nSession Cart State")]
        PyTools --> MockData
        Callbacks --> MockData
    end

    subgraph Toolsets["5. OpenAPI Toolsets\n(platform-native HTTP — not sandboxed)"]
        FetchProfile["fetch_user_profile"]
        AddMemory["add_user_memory"]
        UpdatePrefs["update_user_preferences"]
    end

    subgraph WidgetTools["6. Widget Tool\n(platform-native, model-invoked)"]
        Carousel["show_product_carousel\n(PRODUCT_CAROUSEL)"]
    end

    subgraph Memory["7. Persistent Memory Tier"]
        Microservice["shopping-user-service\n(FastAPI on Cloud Run)"]
        Firestore[("Firestore\nuser_profiles collection")]
        Microservice --> Firestore
    end

    Widget -->|"User Message"| Root
    Root --> ShopAgent
    Root --> FeedAgent
    ShopAgent --> PyTools
    ShopAgent --> Carousel
    ShopAgent --> FetchProfile & AddMemory & UpdatePrefs
    FeedAgent --> PyTools
    FeedAgent --> AddMemory
    FetchProfile & AddMemory & UpdatePrefs --> Microservice
    Carousel -->|"Image Carousel Card"| Widget
    ShopAgent & FeedAgent -->|"Text Response"| Widget
```

---

## 📁 Repository Structure

```
ShoppingAssistantAgent/
├── Shopping-Assistant-Agent-PRD.md  # Product Requirements Document
├── Shopping-Assistant-Agent-TDD.md  # Technical Design Document (TDD v2.1)
├── README.md                        # Project Documentation
├── app.json                         # CX Agent Studio Application Manifest (RootAgent)
├── pyproject.toml                   # Project dependencies and test config
├── gecx-config.toml                 # Multi-Environment Deployment Profiles (dev, staging, prod)
├── .github/
│   └── workflows/
│       ├── ci.yml                   # CI Quality Gate (cxas lint, validate_schemas, pytest, evals)
│       └── cd.yml                   # CD Deployment (GCP Workload Identity promotion)
├── agents/
│   ├── RootAgent/
│   │   ├── RootAgent.json           # RootAgent manifest & sub-agent bindings
│   │   ├── instruction.txt          # Supervisor routing system prompt (<role>, <step>)
│   │   └── before_agent_callbacks/  # Hook: Seeding user_id/user_name defaults for RootAgent
│   ├── ShoppingAssistant/
│   │   ├── ShoppingAssistant.json   # ShoppingAssistant manifest, tools & toolsets
│   │   ├── instruction.txt          # Product discovery, cart & memory-write prompt (<role>, <step>)
│   │   ├── before_agent_callbacks/  # Hook: Seeding context for ShoppingAssistant
│   │   ├── before_tool_callbacks/   # Hook: Argument sanitization
│   │   └── after_tool_callbacks/    # Hook: Server-side cart arithmetic & search_results/feedback state
│   └── FeedbackAgent/
│       ├── FeedbackAgent.json       # FeedbackAgent manifest, tools & toolsets
│       ├── instruction.txt          # Feedback collection & memory-write prompt (<role>, <step>)
│       ├── before_agent_callbacks/  # Hook: Seeding context for FeedbackAgent
│       └── after_tool_callbacks/    # Hook: Verification after feedback submission
├── tools/                            # CXAS pythonFunction / clientFunction tools (self-contained, sandboxed)
│   ├── get_discount/
│   │   ├── get_discount.json
│   │   └── python_function/python_code.py
│   ├── search_catalog/
│   │   ├── search_catalog.json
│   │   └── python_function/python_code.py
│   ├── add_to_cart/
│   │   ├── add_to_cart.json
│   │   └── python_function/python_code.py
│   ├── get_cart/
│   │   ├── get_cart.json
│   │   └── python_function/python_code.py
│   ├── remove_from_cart/
│   │   ├── remove_from_cart.json
│   │   └── python_function/python_code.py
│   ├── submit_feedback/
│   │   ├── submit_feedback.json
│   │   └── python_function/python_code.py
│   ├── end_session/
│   │   └── end_session.json        # CXAS Client Tool Manifest (clientFunction)
│   └── show_product_carousel/
│       └── show_product_carousel.json  # CXAS Widget Tool (widgetTool, PRODUCT_CAROUSEL) — model-invoked, platform-rendered
├── toolsets/                         # CXAS OpenAPI toolsets — platform-executed HTTP calls (not sandboxed)
│   ├── fetch_user_profile/
│   │   ├── fetch_user_profile.json           # Toolset manifest (openApiToolset)
│   │   └── open_api_toolset/open_api_schema.yaml  # GET /api/v1/users/{user_id}
│   ├── add_user_memory/
│   │   ├── add_user_memory.json
│   │   └── open_api_toolset/open_api_schema.yaml  # POST /api/v1/users/{user_id}/memories
│   └── update_user_preferences/
│       ├── update_user_preferences.json
│       └── open_api_toolset/open_api_schema.yaml  # POST /api/v1/users/{user_id}/preferences
├── microservice/                     # FastAPI + Firestore backend for the three toolsets above
│   ├── main.py                      # REST endpoints consumed by the OpenAPI toolsets above
│   ├── firestore_service.py         # Firestore read/write layer
│   ├── Dockerfile / deploy.sh       # Cloud Run deployment (`shopping-user-service`)
│   └── test_main.py                 # Microservice unit tests (pytest)
├── services/
│   ├── interfaces.py                # Abstract Base Classes for services
│   ├── user_service.py              # User service implementation
│   ├── discount_service.py          # Discount service implementation
│   ├── catalog_service.py           # Product catalog service implementation
│   ├── cart_service.py              # Session cart service implementation
│   └── feedback_service.py          # Customer feedback service implementation
├── data/
│   ├── mock_users.json              # Mock user profile database
│   ├── membership_discounts.json    # Membership tier discount mapping
│   ├── mock_catalog.json            # Mock product catalog with images
│   └── mock_feedback.json           # Persistent feedback store
├── evaluations/                      # CXAS SCRAPI official evaluation definitions & runner
│   ├── tc_01_gold_greeting/
│   │   └── tc_01_gold_greeting.json # Golden evaluation definition
│   ├── tc_06_guest_user_flow/
│   │   └── tc_06_guest_user_flow.json # Scenario evaluation definition
│   ├── tc_08_end_to_end_multi_agent_journey/
│   │   └── tc_08_end_to_end_multi_agent_journey.json # Scenario evaluation definition
│   └── run_evals.py                 # Local multi-agent simulation evaluation runner
├── tests/
│   └── test_services.py             # Unit test suite (unittest)
├── web/                               # Standalone web widget embed test page (static, not part of the CXAS app)
│   ├── index.html                   # Embeds Google's chat-messenger SDK against the deployed dev app
│   └── README.md                    # Local run instructions & token-broker auth notes
└── scripts/
    ├── build_app.py                 # cxas-scrapi multi-environment deployer (dev, staging, prod); also
    │                                 # re-applies agent↔toolset bindings after push (see below)
    ├── push_all_evals.py            # Syncs all Golden & Scenario evals to CXAS
    ├── test_interactive_session.py  # Interactive multi-agent demo simulation
    ├── smoke_test_routing.py        # Live routing check against a deployed app (see Testing)
    └── validate_schemas.py          # Schema & manifest validation script
```

---

## 🛡️ Guardrails & Global Observability Settings

All guardrail boundaries and analytics logging settings are defined globally at the application level in `app.json`.

### 1. Guardrail Configurations
- **Blocklist**: Deterministic redaction of competitor brand names (`Nike`, `Adidas`, etc.) from agent responses, and sensitive user inputs (Credit Card regex, SSN regex, and basic profanity).
- **Custom Prompt Guard**: Screening model input against jailbreak / injection attempts to block off-topic prompt overrides.
- **Natural Language Rules**: 7 LLM-evaluated behavioral policies ensuring transaction security, strict product alignment, and preventing incorrect discount applications or medical advice.

### 2. Global Logging & Storage
- **Cloud Logging**: Streams turn-by-turn trace entries to Google Cloud Logging (`enableCloudLogging: true`).
- **BigQuery Export**: Automatically streams conversation histories to `shopping_assistant_logs` for analytics.

---

## 🧠 Persistent User Memory (Firestore)

**Design principle:** the live shopping cart is session-scoped only (CXAS session state, `{cart}`) and is *never* written to Firestore. Firestore exists solely to hold durable *knowledge* about a user — across two complementary channels — so future sessions can give better recommendations. This intentionally keeps transient cart state separate from durable user knowledge and avoids syncing the cart on every add/remove.

### 1. Two memory channels
- **Free-text facts** (`memories: []`) — short natural-language sentences for narrative/episodic context that doesn't fit a fixed shape (e.g. *"Rated shopping experience 5/5, praised product recommendations."*).
- **Structured preferences** (`preferences: {}`) — bounded, overwritable fields aligned to `search_catalog`'s own filter parameters, so they can double as default search filters, not just stored trivia: `preferred_categories`, `preferred_sports`, `preferred_brands`, `shoe_size`, `apparel_size`, `equipment_size`, `price_max`.

### 2. Read & write paths
- **`fetch_user_profile`** (`toolsets/fetch_user_profile/`): called at the start of a `ShoppingAssistant` session with `user_id`, returns `user_name`, `membership_tier`, `memories`, and `preferences` — which seed `{long_term_memories}` and `{preferences}` for the model to reference.
- **`add_user_memory`** (`toolsets/add_user_memory/`): appends one new free-text fact. Bound to both `ShoppingAssistant` and `FeedbackAgent`.
- **`update_user_preferences`** (`toolsets/update_user_preferences/`): merges partial preference updates — list fields (`preferred_*`) are unioned + deduped with existing values, scalar fields (sizes, `price_max`) overwrite. Bound to `ShoppingAssistant` only.
- All three wrap REST endpoints on the `shopping-user-service` Cloud Run microservice (`microservice/`), which reads/writes the `user_profiles` collection in Firestore.

### 3. When each gets written
Because writes must be explicit model-invoked tool calls (see the sandboxing note below — a callback cannot make this HTTP call itself), the instructions trigger writes at natural, reliably-detectable conversation milestones rather than on every action:
- **`FeedbackAgent`**, right after `submit_feedback` succeeds — a deterministic, always-fires trigger — writes an `add_user_memory` fact summarizing the rating/sentiment.
- **`ShoppingAssistant`**, `update_user_preferences` fires **immediately** when the user states an explicit preference mid-conversation ("I wear size 10", "keep me under $150") — no need to wait for session end.
- **`ShoppingAssistant`**, at session close (goodbye, "that's all") — writes one consolidated `add_user_memory` fact, and falls back to `update_user_preferences` for any *inferred-but-unstated* signal (e.g. repeated searches for one sport) that wasn't already captured explicitly. Both are skipped for a session with no real activity.
- `search_catalog` falls back to `{preferences}` as default filters whenever the user doesn't specify a criterion, without overriding one they did specify.

### 4. Example
*Session 1*: user `u_1030` (Jordan, Silver) states "I wear size 10, keep me under $150" — `update_user_preferences` fires immediately. Later, adds a StormFlex jacket to cart and says goodbye — `ShoppingAssistant` calls `add_user_memory` with: *"Jordan (Silver member) showed interest in the StormFlex Waterproof Trail Jacket and added it to the cart."*
*Session 2*: a new session for `u_1030` calls `fetch_user_profile`, which returns both the fact (in `memories`) and `{shoe_size: "10", price_max: 150}` (in `preferences`) — letting the assistant personalize recommendations and pre-filter searches, without ever having persisted the cart itself.

---

## 🛠️ CXAS Platform Architecture & Self-Contained Python Tools

### 1. Isolated Google Cloud Execution Sandbox
In **Gemini Enterprise for Customer Experience (CX Agent Studio / CES API)**, Python tools defined via `pythonFunction` run in an isolated execution sandbox hosted on Google Cloud.
- **Self-Contained Tool Requirement**: Tool source files (`tools/<tool_name>/python_function/python_code.py`) MUST be self-contained and use standard Python libraries (`typing`, `json`, `datetime`, `random`, `math`). External local module imports (such as `from services...`) cause GCP's Python parser to fail with `400 Bad Request: No module named 'services'`, which prevents tools from being registered in Agent Studio.
- **Embedded Mock Data**: Tools include inline mock data fallback structures for catalog, user profile, discount rates, cart memory, and feedback logging to ensure 100% standalone reliability on GCP while maintaining compatibility with local unit test suites.
- **No outbound network access**: this sandbox (and the callback execution environment — `before_agent`/`after_tool`/etc. are plain Python running the same way) has *zero* egress — confirmed by direct testing: any `urllib`/`requests` call from inside a `pythonFunction` or callback fails immediately with DNS resolution or "network unreachable" errors, regardless of target host. Any call to an external HTTP API (like the Firestore microservice) **must** go through a CXAS OpenAPI tool/toolset instead — that's a platform-native call executed outside the sandbox, not sandboxed Python code. This is why `fetch_user_profile`, `add_user_memory`, and `update_user_preferences` are `toolsets/` OpenAPI resources rather than `pythonFunction` tools that just call `requests.post(...)`.

### 2. OpenAPI Tools vs. Toolsets (`toolsets/`)
Wrapping an external REST endpoint for CXAS to call requires care — the two resource shapes are easy to conflate and the platform doesn't clearly error on the wrong one:
- A **`Tool`** (lives under `tools/<name>/`) has an `openApiTool` field (singular) for a *single* HTTP operation.
- A **`Toolset`** (lives under `toolsets/<name>/`, schema at `toolsets/<name>/open_api_toolset/open_api_schema.yaml`) has an `openApiToolset` field and can expose *multiple* operations from one schema. In practice, pushing an OpenAPI-based tool config always gets created server-side as a `Toolset` (confirmed empirically), regardless of which field name was used locally — so OpenAPI tools in this repo consistently live under `toolsets/`, not `tools/`.
- The resolved tool name the model actually calls is `{toolset_name}_{operationId}` (e.g. `fetch_user_profile_fetch_user_profile`) — that compound name is what `instruction.txt`'s `{@TOOL: ...}` placeholders must reference.
- Binding a toolset to an agent uses the agent manifest's separate `toolsets` array (`[{"toolset": "<name>", "toolIds": ["<operationId>"]}]`), **not** the `tools` array — a plain tool-name string there will hard-fail the push with `Reference '<name>' of type 'ces.googleapis.com/Tool' not found.`
- **Schema gotcha**: a request-body property typed as a schemaless `{"type": "object"}` silently arrives as `{}` server-side — the platform's OpenAPI executor only forwards fields it can resolve through explicit nested `properties`. Any object-typed request body field needs its full shape spelled out in the schema (see `toolsets/add_user_memory/open_api_toolset/open_api_schema.yaml` for a worked example) or the actual data gets dropped in transit while the call still reports success. Note this is specific to nested *objects* — a top-level array-of-strings field (e.g. `update_user_preferences`'s `preferred_categories: string[]`) passes through fine without needing extra structure.

### 3. Widget Tools — Rich UI Without a Callback (`tools/show_product_carousel/`)
Product images are rendered via a `WidgetTool` (`tools/show_product_carousel/`), not a callback formatting a custom JSON payload — an earlier version tried exactly that (`after_model_callback` building a `custom_payload`/`rich_widgets` field) and it could never have worked: proven via live instrumentation that `after_model_callback`'s state view only reflects what was already persisted *before* the current turn began, never `search_results`/`cart`/`discount_pct` set by tools called earlier in the same turn. The callback and its `afterModelCallbacks` registration have been removed.
- `WidgetTool` is a oneof variant on the `Tool` resource — same family as `pythonFunction`/`openApiTool` — so it lives under `tools/<name>/<name>.json` like any other tool, no separate `widgets/` directory (one doesn't exist in `cxas push`'s bundle; if it did, files there would be silently dropped, the same class of bug hit with toolsets/guardrails).
- The model calls it directly, the same way it calls `add_to_cart` — no callback, no state read, no timing issue. `ShoppingAssistant`'s instruction tells it to call `show_product_carousel` right after `search_catalog`, building `productDetails` from the results it just saw in that tool's own response.
- The platform ships pre-built `widgetType`s for common patterns (`PRODUCT_CAROUSEL`, `PRODUCT_DETAILS`, `ORDER_SUMMARY`, `QUICK_ACTIONS`, etc.) with a fixed `parameters` schema per type — this repo uses `PRODUCT_CAROUSEL` (`productDetails: [{title, subtitle, price, productId, imageUris, uri}]`).
- `cxas-scrapi`'s scaffolding CLI has no widget template yet. The reliable way to get the exact parameter schema for a given `widgetType` is to build one once in CX Agent Studio's Widgets panel, then `cxas pull <app> --target-dir <scratch-dir>` (into a **separate** directory, not `--overwrite` on the repo) and copy the generated `tools/<name>/<name>.json` in — that's how this one was created.

### 4. Native SCRAPI Deployment Pipeline (`scripts/build_app.py`)
Deploying an application via `python scripts/build_app.py --env <dev|staging|prod>` (or via GitHub Actions CD) executes a two-phase process:
1. **Pre-Flight Quality Gates**: Automatically cleans `__pycache__`, executes the unit test suite (`python -m unittest discover tests/`), and runs schema validation (`scripts/validate_schemas.py`). If any test fails, deployment is aborted before reaching GCP.
2. **Native SCRAPI CLI Push (`cxas push`)**: Resolves the target app resource path (`projects/{project}/locations/{location}/apps/{app_id}`) from `gecx-config.toml` and delegates synchronization directly to the native `cxas push` CLI toolchain.
3. **Toolset Binding Reconciliation**: `cxas push`'s bulk import correctly creates/updates `Toolset` resources but silently drops each agent's `toolsets` binding declared in its manifest (a known gap in the current `cxas-scrapi` bulk-import path). `build_app.py` re-applies these bindings after every push via a direct Agent Service API call (`update_agent` with an explicit field mask), reading the `toolsets` array straight out of each `agents/*/*.json`. This step is generic — any agent/toolset pair declared in the manifests gets reconciled automatically, no script changes needed when adding a new toolset.

### 5. CXAS Session Variable Mutation Patterns
State persistence across agents and turns follows specific CXAS platform rules:
- **App-Scoped State**: All session variables (such as `cart`, `user_name`, `membership_tier`) are declared globally at the App level (`app.json`). Once declared, state is shared transparently across Root and sub-agents during handoffs.
- **Tool State Mutation via `context.state`**: Python tools must explicitly mutate state using `context.state["cart"] = cart` (or `set_variable("cart", cart)`). Returning dictionary payloads containing `{"updatedVariables": ...}` alone does not persist state across turns in the CXAS Agent Engine runtime.
- **Robust Callback State Helpers**: Callback helper functions (`get_state`, `set_state_var`) must handle both standard Python `dict` types and CXAS runtime mapping objects (`MapComposite`, `State`). State setters must avoid returning early when encountering dictionary targets so that updates commit directly to `callback_context.state`.

### 6. RootAgent Never Answers Directly
`RootAgent` only detects intent and transfers — it has no `fetch_user_profile` binding and never will (see below). Every user-facing response, including a bare "hello", must come from a sub-agent that owns the relevant personalization/tools. Concretely: bare greetings transfer to `ShoppingAssistant` rather than `RootAgent` replying with a generic message itself — the earlier version did the latter, and since `RootAgent` never fetches the profile, greetings were silently never personalized. `scripts/smoke_test_routing.py` exists specifically to catch a regression of this kind, since `evaluations/run_evals.py` never exercises `RootAgent`'s routing at all.

Deliberately **not** giving `RootAgent` its own `fetch_user_profile` call, even to greet by name pre-routing: `RootAgent` runs on literally every turn, so it would either fetch on every single message (redundant — `ShoppingAssistant` already fetches once on entry) or need conditional "only fetch if about to greet" logic that reimplements what routing already decides. It would also tax every `FeedbackAgent`-only session with a Firestore round-trip it never uses.

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
- Python `3.10` or higher
- Git
- `astral-uv`

### 2. Installation
Clone the repository and initialize the virtual environment:
```bash
uv venv --python 3.10
uv pip install -e .
```

---

## 🧪 Testing & Verification

### Run CXAS Deterministic Linter
Validates directory layout, protobuf schemas, tool configurations, and prompt structure (Target: 0 errors). Now run in CI (`.github/workflows/ci.yml`) via `pip install -e .`, so it always uses the pinned `cxas-scrapi` version — **do not** bump `cxas-scrapi` past `1.7.0` without checking first: `1.8.0` shipped a docstring-parsing bug in its V001/V004 schema-validation rules that misflags genuinely `Optional` fields (e.g. `OpenApiToolset.api_authentication`) as missing/required whenever their description text happens to contain the word "required" as prose:
```bash
uv run cxas lint
```

### Run Schema & Manifest Validation
Validates `app.json`, agent JSON manifests, `instruction.txt` files, and JSON data files:
```bash
uv run python scripts/validate_schemas.py
```

### Run Unit Test Suite
Executes unit tests for services, tools, and callback logic:
```bash
uv run python -m unittest discover tests/
```

### Run Microservice Unit Tests
Executes tests for the Firestore-backed `shopping-user-service` (`fetch_user_profile` / `add_user_memory` / `update_user_preferences` backend):
```bash
cd microservice && pip install -r requirements.txt && pytest test_main.py
```

### Run Scenario Evaluations & Multi-Turn Simulations
Executes 9 automated evaluation test cases covering member tier greetings (Gold, Silver, Bronze, Guest), catalog searches, server-side cart pricing & item removals, feedback submissions, and end-to-end multi-agent journey flows:
```bash
uv run python evaluations/run_evals.py
```


### Push Evaluations to CXAS Studio
Push individual evaluations or all Golden and Scenario evaluations to CX Agent Studio:
```bash
# Push an individual evaluation file via SCRAPI CLI
uv run cxas push-eval --app_name projects/ecom-cx-agent/locations/us/apps/shopping-assistant-app-dev \
    --file evaluations/tc_06_guest_user_flow/tc_06_guest_user_flow.json

# Push all Golden & Scenario evaluations
uv run python scripts/push_all_evals.py projects/ecom-cx-agent/locations/us/apps/shopping-assistant-app-dev
```

### Run Interactive Multi-Agent Demo
Simulates an interactive customer turn-by-turn conversation:
```bash
uv run python scripts/test_interactive_session.py
```

### Run Live Routing Smoke Test
`run_evals.py` only simulates ShoppingAssistant's own callback chain locally — it never exercises RootAgent's actual routing/transfer behavior. This script drives real conversation turns against a *deployed* app via the CES Sessions API and checks that RootAgent transfers greetings and shop/feedback intent to the right sub-agent. Needs live GCP credentials and burns model quota, so it's not wired into CI — run manually after changing any `agents/*/instruction.txt` or `agents/*/*.json`:
```bash
uv run python scripts/smoke_test_routing.py --env dev
```

---

## 🔐 Keyless Authentication Setup (GCP Workload Identity Federation)

To enable automated CD deployment via GitHub Actions without storing long-lived service account keys:

```bash
# 1. Set variables
export PROJECT_ID="ecom-cx-agent"
export REPO="Sunilrana1978/ShoppingAssistantagent"
export SA_NAME="github-actions-deployer"
export POOL_NAME="github-pool"
export PROVIDER_NAME="github-provider"

# 2. Get GCP Project Number
export PROJECT_NUM=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# 3. Create Service Account & Grant IAM Roles
gcloud iam service-accounts create $SA_NAME --project=$PROJECT_ID --display-name="GitHub Actions Deployer"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/dialogflow.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/aiplatform.admin"

# 4. Create Workload Identity Pool & OIDC Provider
gcloud iam workload-identity-pools create $POOL_NAME --project=$PROJECT_ID --location="global" --display-name="GitHub Actions Pool"

gcloud iam workload-identity-pools providers create-oidc $PROVIDER_NAME \
    --project=$PROJECT_ID --location="global" --workload-identity-pool=$POOL_NAME \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository == '$REPO'" \
    --issuer-uri="https://token.actions.githubusercontent.com"

# 5. Bind Service Account to GitHub Repository
gcloud iam service-accounts add-iam-policy-binding "${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --project=$PROJECT_ID \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUM}/locations/global/workloadIdentityPools/${POOL_NAME}/attribute.repository/${REPO}"

# 6. Set GitHub Repository Secrets
gh secret set GCP_SA_EMAIL --body "${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" --repo $REPO
gh secret set GCP_WIF_PROVIDER --body "projects/${PROJECT_NUM}/locations/global/workloadIdentityPools/${POOL_NAME}/providers/${PROVIDER_NAME}" --repo $REPO
```

---

## 🚢 Deployment to GCP (`ecom-cx-agent`, region: `us`)

### Method 1: Automated Deployment via GitHub Actions (Recommended)
- **Deploy to STAGING**: Merge your Pull Request or push commits to `main`. GitHub Actions automatically authenticates via WIF and deploys to `ecom-cx-agent` (`shopping-assistant-app-staging`).
- **Deploy to PRODUCTION**: Create a Git release tag (e.g., `git tag v1.0.0 && git push origin v1.0.0`). GitHub Actions automatically deploys to `ecom-cx-agent` (`shopping-assistant-app-prod`).

### Method 2: Deployment via Terminal CLI / Script
```bash
# 1. Authenticate with Google Cloud
gcloud auth application-default login
gcloud config set project ecom-cx-agent

# 2. Deploy to DEV environment
uv run python scripts/build_app.py --env dev
# or: uv run cxas push --to projects/ecom-cx-agent/locations/us/apps/shopping-assistant-app-dev

# 3. Deploy to STAGING environment
uv run python scripts/build_app.py --env staging
# or: uv run cxas push --to projects/ecom-cx-agent/locations/us/apps/shopping-assistant-app-staging

# 4. Deploy to PROD environment
uv run python scripts/build_app.py --env prod
# or: uv run cxas push --to projects/ecom-cx-agent/locations/us/apps/shopping-assistant-app-prod
```

---

## 💬 Web Widget Embed (Local Test Page)

`web/` is a standalone static page — no build step, no dependencies, not touched by `cxas push`/`build_app.py` — that embeds Google's prebuilt `chat-messenger` SDK against a specific CXAS `Deployment` resource, for testing the deployed web widget outside of Studio's own Preview.

```bash
cd web && python3 -m http.server 8000   # open http://localhost:8000
```

### Authentication: the token broker, not a manually-supplied token
The `chat-messenger` SDK **always requires an `accessToken`** on its registered context, client-side — regardless of the deployment's `security_settings.enable_public_access` flag. Without one, it throws `Error: No access token found.` before ever making a network call, and does so silently: no console error, no failed request, nothing but a swallowed exception (found by pausing the debugger on *caught* exceptions in the SDK's minified source). `enable_public_access` only controls what the *server* will accept — it doesn't remove the *client's* need for a token.

The fix is **not** to mint a token once and hardcode it (`WidgetService.GenerateChatToken` tokens are scoped to a single session name, but the SDK generates its own session ID internally at runtime, so a static token won't match). Instead, `web/index.html` passes `tokenBroker: { enableTokenBroker: true }` into `chatSdk.prebuilts.ces.createContext({...})` — this makes the SDK automatically POST to the deployment's public `:generateChatToken` REST endpoint and self-manage the token whenever it opens a session:

```js
chatSdk.registerContext(
  chatSdk.prebuilts.ces.createContext({
    deploymentName: "projects/{project_number}/locations/{location}/apps/{app}/deployments/{deployment}",
    tokenBroker: { enableTokenBroker: true }
  }),
);
```

That endpoint only accepts unauthenticated calls because this deployment's channel profile has `enable_public_access: true` (and `enable_recaptcha: false`, so no reCAPTCHA sitekey is needed either). Pointing this page at a different deployment requires that deployment to have the same `enable_public_access` setting, or the token broker fails the same silent way.

Note `deploymentName` uses the numeric GCP **project number**, not the project ID — a different resource path shape than the `App` name (`projects/ecom-cx-agent/...`) used everywhere else in this repo.

---

## 📸 Screenshots

### 1. Multi-Agent Connection Graph in CX Agent Studio
![Multi-Agent Connection Graph](assets/agent_graph.png)

### 2. Deployed Applications List (dev, staging, prod)
![Deployed Applications List](assets/deployed_apps.png)

---

## 📝 Document References
- [Product Requirements Document (PRD)](file:///Users/sunilkumar/gcp/ShoppingAssistantAgent/Shopping-Assistant-Agent-PRD.md)
- [Technical Design Document (TDD v2.1)](file:///Users/sunilkumar/gcp/ShoppingAssistantAgent/Shopping-Assistant-Agent-TDD.md)

