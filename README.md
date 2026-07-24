# Sporting Goods Multi-Agent Shopping & Feedback Assistant

A multi-agent conversational application for a sporting goods storefront (shoes, apparel, equipment) built on **Customer Experience Agent Studio (CX Agent Studio)** — part of **Gemini Enterprise for Customer Experience** — and managed programmatically using **`cxas-scrapi`** (`GoogleCloudPlatform/cxas-scrapi`).

---

## 🌟 Overview & Key Features

The application features a **Multi-Agent Router Architecture** driven by natural-language XML instructions, Python code tools, execution callbacks, dynamic session variables, and a pluggable service abstraction layer:

- **Root Router Agent (`RootAgent`)**: Central supervisor that detects customer intent and routes between shopping discovery and customer feedback.
- **Shopping Assistant (`ShoppingAssistant`)**: Greets members, surfaces membership-tier discounts, searches product catalogs based on natural-language queries, and manages session shopping carts.
- **Customer Feedback Agent (`FeedbackAgent`)**: Collects 1 to 5 star ratings and customer feedback comments, logging them into analytics.
- **Membership Discount Engine**: Automatically applies member discounts (**Gold: 15%**, **Silver: 10%**, **Bronze: 5%**, **Guest: 0%**) to product prices and cart totals.
- **Server-Side Pricing Math**: Uses `after_tool_callback` Python hooks to calculate exact float arithmetic for cart subtotals, discount amounts, and grand totals server-side.
- **Rich Response Widgets**: Renders product recommendations and cart line items as structured, image-bearing Info Card UI widgets.
- **Service Abstraction Layer**: Data access is isolated behind `IUserService`, `IDiscountService`, `ICatalogService`, `ICartService`, and `IFeedbackService` interfaces — currently backed by mock JSON files, ready to swap for real REST/OpenAPI backends.
- **CI/CD & Environment Promotion**: Fully configured GitHub Actions workflows for continuous integration quality gates (`.github/workflows/ci.yml`) and multi-environment deployment (`.github/workflows/cd.yml`).

---

## 🏗️ Architecture Diagram

```mermaid
flowchart LR
    subgraph Client["1. Client Layer"]
        Widget["Web Chat Widget / Channel"]
    end

    subgraph Router["2. Router Agent Layer"]
        Root["RootAgent (Supervisor)\n- Intent Detection\n- Sub-agent Routing"]
    end

    subgraph DomainAgents["3. Specialized Domain Agents"]
        ShopAgent["ShoppingAssistant Agent\n(Catalog Search & Cart)"]
        FeedAgent["FeedbackAgent\n(Rating & Feedback Collection)"]
    end

    subgraph ToolsHooks["4. Callbacks & Tools Layer"]
        ShopTools["Shopping Tools\n(Profile, Discount, Search, Cart)"]
        FeedTools["Feedback Tools\n(submit_feedback)"]
        Callbacks["Python Callbacks\n(before_agent, after_tool, after_model)"]
    end

    subgraph DataStore["5. Service & Data Tier"]
        Services["Services (User, Discount, Catalog, Cart, Feedback)"]
        Storage[("JSON Data Store &\nSession Cart Memory")]
        Services --> Storage
    end

    Widget -->|"User Message"| Root
    Root -->|"Intent: Shop / Browse"| ShopAgent
    Root -->|"Intent: Feedback / Review"| FeedAgent
    ShopAgent --> ShopTools
    FeedAgent --> FeedTools
    ShopTools & FeedTools --> Callbacks --> Services
    ShopAgent & FeedAgent -->|"Rich Cards / Text Response"| Widget
```

---

## 📁 Repository Structure

```
ShoppingAssistantAgent/
├── Shopping-Assistant-Agent-PRD.md  # Product Requirements Document
├── Shopping-Assistant-Agent-TDD.md  # Technical Design Document (TDD v2.0)
├── README.md                        # Project Documentation
├── app.json                         # CX Agent Studio Application Manifest
├── pyproject.toml                   # Project dependencies and test config
├── .github/
│   └── workflows/
│       ├── ci.yml                   # CI Quality Gate (Schema linting, pytest, evals)
│       └── cd.yml                   # CD Deployment (GCP Workload Identity promotion)
├── environments/
│   ├── dev.environment.json         # Dev environment target config (ecom-cx-agent)
│   ├── staging.environment.json     # Staging environment target config (ecom-cx-agent)
│   └── prod.environment.json        # Production environment target config (ecom-cx-agent)
├── agents/
│   ├── root_agent/
│   │   ├── agent.json               # RootAgent manifest & sub-agent bindings
│   │   ├── instructions.xml         # Supervisor routing system prompt
│   │   └── variables.json           # Router variables schema
│   ├── shopping_assistant/
│   │   ├── agent.json               # ShoppingAssistant manifest & tools
│   │   ├── instructions.xml         # Product discovery & cart system prompt
│   │   └── variables.json           # Shopping variables schema
│   └── feedback_agent/
│       ├── agent.json               # FeedbackAgent manifest & tools
│       ├── instructions.xml         # Feedback collection system prompt
│       └── variables.json           # Feedback variables schema
├── tools/
│   ├── get_user_profile.py          # Python tool: User profile lookup
│   ├── get_discount.py              # Python tool: Membership discount lookup
│   ├── search_catalog.py            # Python tool: Catalog search & filtering
│   ├── add_to_cart.py               # Python tool: Add item SKU/qty to session cart
│   ├── get_cart.py                  # Python tool: Active cart details & totals
│   ├── remove_from_cart.py          # Python tool: Cart item removal
│   └── submit_feedback.py           # Python tool: Submit star rating & comments
├── callbacks/
│   ├── before_agent.py              # Hook: Context seeding from channel payload
│   ├── after_tool.py                # Hook: Server-side cart arithmetic & feedback state
│   ├── before_tool.py               # Hook: Argument sanitization
│   └── after_model.py               # Hook: Rich Info Card payload formatting
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
├── evals/
│   ├── test_cases.json              # Evaluation simulation test suite
│   └── run_evals.py                 # cxas-scrapi simulation runner
├── tests/
│   └── test_services.py             # Unit test suite (unittest)
└── scripts/
    ├── validate_schemas.py          # Schema & manifest validation script
    ├── build_app.py                 # cxas-scrapi multi-environment deployer
    └── test_interactive_session.py  # Interactive multi-agent demo simulation
```

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
- Python `3.9` or higher
- Git

### 2. Installation
Clone the repository and install required dependencies:
```bash
pip install -e .
# or
pip install pydantic cxas-scrapi
```

---

## 🧪 Testing & Verification

### Run Schema & Manifest Validation
Validates `app.json`, `agent.json`, `instructions.xml`, and JSON data files:
```bash
python scripts/validate_schemas.py
```

### Run Unit Test Suite
Executes unit tests for services, tools, and callback logic:
```bash
python -m unittest discover tests/
```

### Run Automated Simulation Evaluations
Executes multi-turn conversation simulations covering tier discount greetings, catalog searches, server-side cart arithmetic, and feedback submissions:
```bash
python evals/run_evals.py
```

### Run Interactive Multi-Agent Demo
Simulates an interactive customer turn-by-turn conversation:
```bash
python scripts/test_interactive_session.py
```

---

## 🚢 Deployment to GCP (`ecom-cx-agent`, region: `us`)

### Method 1: Automated Deployment via GitHub Actions (Recommended)
- **Deploy to STAGING**: Merge your Pull Request or push commits to `main`. GitHub Actions automatically deploys to `ecom-cx-agent` (`shopping-assistant-app-staging`).
- **Deploy to PRODUCTION**: Create a Git release tag (e.g., `git tag v1.0.0 && git push origin v1.0.0`). GitHub Actions automatically deploys to `ecom-cx-agent` (`shopping-assistant-app-prod`).

### Method 2: Deployment via Terminal CLI / Script
```bash
# 1. Authenticate with Google Cloud
gcloud auth application-default login
gcloud config set project ecom-cx-agent

# 2. Deploy to DEV environment
python scripts/build_app.py --env dev
# or: cxas push --environment environments/dev.environment.json

# 3. Deploy to STAGING environment
python scripts/build_app.py --env staging
# or: cxas push --environment environments/staging.environment.json

# 4. Deploy to PROD environment
python scripts/build_app.py --env prod
# or: cxas push --environment environments/prod.environment.json
```

### Method 3: Import via CX Agent Studio Web Console
1. Open **Google Cloud Console** → Navigate to **Gemini Enterprise for Customer Experience** → **CX Agent Studio**.
2. Select GCP Project **`ecom-cx-agent`** and Region **`us`**.
3. Click **Import Application** and select the repository root directory (containing `app.json`).
4. CX Agent Studio will auto-import `RootAgent`, `ShoppingAssistant`, `FeedbackAgent`, instructions, and Python tools.

---

## 📝 Document References
- [Product Requirements Document (PRD)](file:///Users/sunilkumar/gcp/ShoppingAssistantAgent/Shopping-Assistant-Agent-PRD.md)
- [Technical Design Document (TDD v2.0)](file:///Users/sunilkumar/gcp/ShoppingAssistantAgent/Shopping-Assistant-Agent-TDD.md)
