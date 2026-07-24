# Product Requirements Document
## Sporting Goods Shopping Assistant Agent (Gemini Enterprise for Customer Experience — CX Agent Studio)

**Version:** 1.1 (Draft)
**Owner:** Sunil Kumar
**Date:** July 23, 2026
**Platform:** Customer Experience Agent Studio (**CX Agent Studio**), part of **Gemini Enterprise for Customer Experience**

---

## 1. Overview

A conversational shopping assistant for a sporting goods storefront (shoes, apparel, equipment). The agent greets the user, surfaces membership-tier discounts, recommends products from a catalog based on natural-language input, and lets the user add confirmed items to a cart — with product images shown throughout. Built on **CX Agent Studio** — Google's next-generation, minimal-code conversational agent builder, built on the **Agent Development Kit (ADK)** and part of Gemini Enterprise for Customer Experience. The agent is structured as an **App → Agent**, driven by natural-language **Instructions**, **Tools** (Python code, OpenAPI, client function, system, widget tools), **Variables** (static + dynamic), and **Callbacks** (Python hooks at defined points in the turn). All product, membership, and cart data is **mocked** behind a Python tool layer designed to be swapped for real backend APIs without changing the agent design.

## 2. Goals

| # | Goal |
|---|------|
| G1 | Greet every user and clearly state their membership discount at session start |
| G2 | Let users describe what they want in natural language and get relevant product matches with images |
| G3 | Let users confirm a recommended item and add it to cart |
| G4 | Let users view the full cart (items, images, quantities, per-item and total pricing with discount applied) |
| G5 | Keep all data access behind a swappable service layer (mock now, real API later) |
| G6 | Demonstrate clean CX Agent Studio patterns: static/dynamic variables, Python code tools, callbacks, rich response widgets |

### Out of scope (v1)
- Real payment / checkout completion (cart is the end state)
- Real inventory, pricing, or membership APIs (mocked only)
- Multi-language support
- Voice channel (assume text/chat + optional rich content for images)
- Order history / returns

## 3. Users & Personas

- **Guest shopper (no membership):** browses, gets 0% discount, may be prompted to join a program.
- **Bronze / Silver / Gold member:** identified (mocked) at session start, receives tiered discount automatically applied to recommendations and cart.

## 4. Membership & Discount Rules (Mocked)

| Tier | Discount | Example Greeting Line |
|------|----------|------------------------|
| None / Guest | 0% | "You're browsing as a guest — no discount applied. Ask me about membership anytime!" |
| Bronze | 5% | "As a Bronze member, you get 5% off all items today." |
| Silver | 10% | "As a Silver member, you get 10% off all items today." |
| Gold | 15% | "As a Gold member, you get 15% off all items today, plus early access to new arrivals." |

Discount rules live in mock config (`membership-discounts.json`) so percentages can change without touching agent logic — the `get_discount` Python tool reads this file/table, not hardcoded values.

## 5. Conversation Flow (High Level)

```
[Session Start]
   → before_agent_callback fires: seeds session variables (user_id from channel payload)
   → Agent instruction directs: call {@TOOL: get_user_profile} → sets dynamic vars {membership_tier}, {user_name}
   → Agent instruction directs: call {@TOOL: get_discount} → sets dynamic var {discount_pct}
   → Agent (generated from instructions): "Hi {user_name}! ... your {membership_tier} discount is {discount_pct}% today. What are you shopping for?"

[Product Discovery]
   → User: "I need running shoes for trail running, size 10"
   → Agent instruction directs: call {@TOOL: search_catalog} with free-text + any extracted attributes (category, sport, size, brand, price range — the LLM extracts these itself, no separate entity types needed)
   → Tool returns ranked product list (id, name, price, image_url, attributes) → stored in dynamic variable {search_results}
   → Agent responds with a rich response widget presenting top 3 products (image + name + price + discounted price)
   → User: "show me more" / "the second one" / refine ("in blue", "under $100")
   → Agent instruction directs: call {@TOOL: search_catalog} again with refined params → updates {search_results}

[Product Confirmation]
   → User: "Add the trail runners to my cart" / taps a widget action (via sendPrompt-style client callback)
   → Agent (per instructions): "Add {product_name} (size {size}, qty {qty}) to your cart — confirm?"
   → User: "yes"
   → Agent instruction directs: call {@TOOL: add_to_cart} → after_tool_callback recomputes totals with {discount_pct} → updates dynamic variable {cart}

[Cart View]
   → User: "show my cart" (agent instructions make this reachable at any point in the conversation, not tied to a specific page)
   → Agent instruction directs: call {@TOOL: get_cart} → returns items[] with images, subtotal, discount, total
   → Agent responds with a rich response widget rendering the cart with images + running total

[Continue / Checkout stub]
   → "Keep shopping" → back to Product Discovery guidance in the same agent
   → "Checkout" → out-of-scope message per instructions, logged as a future capability
```

## 6. CX Agent Studio Design

### 6.1 Platform structure: App → Agent
In CX Agent Studio, one **App** (`ShoppingAssistantApp`) contains one or more **Agents**. For v1 we use a single primary Agent (`ShoppingAssistant`) driven by natural-language **Instructions** — the LLM (Gemini) handles intent understanding, slot extraction, and routing based on those instructions, calling **Tools** and reading/writing **Variables** as needed. Structured values (size, brand, color, category) are extracted directly as tool call arguments by the model; a Custom Object variable schema can constrain their shape where needed. Anything that should be reachable at any point in the conversation (e.g., "show my cart") is simply stated once in the Instructions rather than requiring a separate routing construct.

### 6.2 Instructions

The Agent's Instructions are the primary design surface — effectively a structured system prompt covering: persona ("helpful sporting-goods shopping assistant"), the greeting + discount behavior, when to call each tool, how to present product/cart results (always via the rich response widget, never as plain text lists), and business rules (e.g., "always show the discounted price alongside the original price"). CX Agent Studio can **restructure** hand-written instructions into XML for better model adherence and **refine** them for clarity — both AI-assisted steps we'll run once the first draft is written.

### 6.3 Variables

| Variable | Type | Static or Dynamic | Set By | Example |
|---|---|---|---|---|
| `business_rules` | Text | **Static** | agent config | discount tiers, presentation rules — compiled into the prompt, rarely changes |
| `user_id` | Text | Dynamic | `before_agent_callback` (from channel payload) | `"u_1029"` |
| `membership_tier` | Text | Dynamic | `get_user_profile` tool | `"gold"` |
| `discount_pct` | Number | Dynamic | `get_discount` tool | `15` |
| `search_results` | List / Custom Object | Dynamic | `search_catalog` tool | array of product objects |
| `cart` | Custom Object | Dynamic | `add_to_cart` / `get_cart` tool (via `after_tool_callback`) | `{items:[...], subtotal, discount, total}` |

Static variables (`{{business_rules}}`) are compiled directly into the prompt for strong adherence to fixed rules and are worth the prompt-cache invalidation cost only when they truly don't change mid-session. Dynamic variables (`{membership_tier}`, `{discount_pct}`, `{cart}`) are updated by tools/callbacks during the session and referenced with single curly braces; they're the right choice for anything that changes per-user or per-turn. The agent itself never writes variables directly — only tools and callbacks can (`context.state["variable_name"] = value` in Python).

### 6.4 Tools

All backend logic is exposed as **Python code tools** (CX Agent Studio's equivalent of webhook fulfillment), each backed by the mock data today and swappable for a real API tomorrow:

| Tool Name | Trigger (per Instructions) | Mock Behavior | Future Real API |
|---|---|---|---|
| `get_user_profile` | Session start | Look up `mock_users.json` by `user_id`, default to `none` tier if not found | Identity/CRM service |
| `get_discount` | Right after profile fetch | Look up `membership_discounts.json` | Promotions/Pricing service |
| `search_catalog` | User describes what they want | Filter `mock_catalog.json` by category/sport/brand/size/price + basic text relevance scoring | Product Catalog / Search API |
| `add_to_cart` | User confirms an item | Append to `mock_cart_store` (session-keyed), recompute totals with discount | Cart Service API |
| `get_cart` | User asks to see cart | Return cart object for the session | Cart Service API |
| `remove_from_cart` (v1.1) | User asks to remove an item | Remove item, recompute totals | Cart Service API |

Each tool is a plain Python function with a typed signature (CX Agent Studio auto-generates the tool schema from it); the mock-vs-real switch lives inside the function body (or behind an env flag), so no agent redesign is needed to go live. OpenAPI tools are the natural upgrade path once a real REST catalog/cart API exists — same tool name, instructions unchanged, only the tool definition swaps from Python to an OpenAPI spec.

### 6.5 Callbacks

Callbacks are Python hooks CX Agent Studio runs at fixed points in the turn — used here for logic that shouldn't live inside a tool or be left to the model:

| Callback | Point in turn | Use here |
|---|---|---|
| `before_agent_callback` | Before the agent is invoked | Seed `user_id` from the channel/session payload before the first model call |
| `after_tool_callback` | After a tool completes, before the model sees the result | After `add_to_cart` / `get_cart`, recompute `subtotal`/`discount_amount`/`total` from `discount_pct` server-side (never trust the model to do the arithmetic) and write the result into the `cart` variable |
| `before_tool_callback` | Before a tool executes | Validate `search_catalog` arguments (e.g., clamp size/price ranges) before hitting the mock/real backend |
| `after_model_callback` | After the model responds | Attach a **custom payload** (JSON) alongside the model's text for any structured client-side action, if the rich response widget mechanism doesn't already cover it |

### 6.6 Rich Response Widgets (Product & Cart Cards)

Product recommendations and the cart view are rendered as **rich response widgets** rather than plain text — CX Agent Studio's supported way to return structured, image-bearing UI. A product/cart card is shaped conceptually like:

```json
{
  "type": "info_card",
  "title": "TrailBlaze Pro Trail Runner",
  "subtitle": "$129.99 → $110.49 (Gold 15% off)",
  "image_url": "https://mock-cdn/products/tb-pro.jpg",
  "action": "add:sku_1029"
}
```
The same widget shape is reused for both product search results and cart line items, keeping the client rendering logic (web widget / channel integration) uniform across both use cases.

## 7. Mock Data Model

### 7.1 `mock_users.json`
```json
{ "u_1029": { "name": "Alex", "membership_tier": "gold" } }
```

### 7.2 `membership_discounts.json`
```json
{ "none": 0, "bronze": 5, "silver": 10, "gold": 15 }
```

### 7.3 `mock_catalog.json`
```json
{
  "sku_1029": {
    "name": "TrailBlaze Pro Trail Runner",
    "category": "shoes",
    "sport": "running",
    "brand": "Northline",
    "price": 129.99,
    "sizes": [8, 9, 10, 11],
    "colors": ["black", "blue"],
    "image_url": "https://mock-cdn/products/tb-pro.jpg",
    "description": "Trail running shoe with grippy outsole and rock plate."
  }
}
```

### 7.4 Cart object (runtime, keyed by session_id)
```json
{
  "items": [
    { "sku": "sku_1029", "name": "TrailBlaze Pro Trail Runner", "qty": 1, "size": 10, "price": 129.99, "image_url": "..." }
  ],
  "subtotal": 129.99,
  "discount_pct": 15,
  "discount_amount": 19.50,
  "total": 110.49
}
```

## 8. Service Layer Abstraction (mock → real)

All Python code tools call an internal `ProductService` / `UserService` / `CartService` interface (e.g., `getUser()`, `searchProducts()`, `addToCart()`). The v1 implementation reads the JSON files above; a v2 implementation calls real REST APIs (or the tool is swapped for an OpenAPI tool entirely). Because the Agent's Instructions only ever reference the tool by name — not its implementation — swapping implementations requires no instruction or agent redesign, only a config/environment change (mock vs. live) inside the tool.

## 9. Non-Functional Requirements

- Tool call p95 latency < 1.5s; CX Agent Studio's async tool-call architecture keeps conversation flowing naturally rather than going silent during longer calls, but latency budgets still apply
- Stateless tools (cart keyed by session, not server memory) so they scale horizontally
- Agent definition (Instructions, Tools, Variables, Callbacks, Guardrails) exported/imported and versioned using CX Agent Studio's built-in versioning (changelogs, one-click rollback) and/or its REST/MCP API for CI/CD promotion (dev → test → prod)
- Discount and catalog data validated with a schema check before deploy
- Evaluations (CX Agent Studio's built-in test-case framework) cover: correct discount greeting per tier, at least one relevant search result for common queries, and correct cart totals after add

## 10. Success Metrics (v1)

- % of sessions where membership discount is correctly greeted and applied
- % of product searches returning at least one relevant result
- Add-to-cart completion rate (recommendation shown → confirmed add)
- Cart view accuracy (images/prices match catalog + discount)

## 11. Open Questions

- Where does `user_id` come from in production (auth token, loyalty card lookup, phone number)?
- Should guest (no membership) users be prompted mid-conversation to join a tier?
- Multi-item cart edits (change size/qty, remove item) — confirmed for v1.1, not v1?
- Real catalog source system for the eventual API swap (PIM, e-commerce platform)?

## 12. Rollout Plan

1. Create the App and Agent in CX Agent Studio; draft Instructions (optionally AI-generated as a starting point, then restructured/refined)
2. Build the Python code tools (`get_user_profile`, `get_discount`, `search_catalog`, `add_to_cart`, `get_cart`) against mock JSON data, plus the `before_agent_callback` / `after_tool_callback` callbacks
3. Build the rich response widgets for product cards and cart view; wire widget actions back to tools
4. Test in the CX Agent Studio **Simulator**; write **Evaluation** test cases for the greeting/discount, search, and cart-total scenarios and run test-case hill climbing to harden them
5. Swap `ProductService`/`UserService`/`CartService` mock implementations for real APIs (or replace individual Python tools with OpenAPI tools) behind a config flag
6. Deploy the agent application (web widget and/or contact-center platform connection) and promote across dev → test → prod using CX Agent Studio versions
