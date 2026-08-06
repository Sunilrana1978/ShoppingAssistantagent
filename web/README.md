# Web Chat UI

Two standalone, static test pages for talking to the deployed Shopping
Assistant app. Neither is pushed by `cxas push`/`build_app.py` — both are
static HTML with no build step and no dependencies.

## `index.html` — custom chat UI (primary)

A fully hand-built chat UI that does **not** use Google's prebuilt
`chat-messenger` SDK. It talks to a new chat-proxy endpoint
(`POST /api/v1/chat/{session_id}/messages`) added to the `shopping-user-service`
microservice (`microservice/`), which itself calls the CES Sessions API
server-side via `cxas_scrapi.core.sessions.Sessions` (ADC credentials — same
mechanism `scripts/smoke_test_routing.py` uses).

This exists because the SDK-based `widget-embed.html` page can't render this
app's rich widget tools (`show_product_carousel`, `show_product_comparison`,
`show_order_summary`) — `index.html` renders them itself from the raw CES
response payload.

### Run locally

```bash
# 1. Start the chat-proxy backend
cd microservice
pip install -r requirements.txt
uvicorn main:app --reload   # listens on :8080 by default

# 2. In another terminal, serve the static page
cd web
python3 -m http.server 8000
```

Open http://localhost:8000, optionally set a `user_id` (e.g. `u_1029` for a
Gold member, or leave blank for a guest session), and chat.

### Config

- `API_BASE` at the top of the inline `<script>` block in `index.html` points
  at the microservice. Defaults to `http://localhost:8080`; change it to the
  deployed Cloud Run URL (see `microservice/deploy.sh`'s printed
  `SERVICE_URL`) to talk to a live backend.
- The backend resolves which CXAS app/env to call from `GCP_PROJECT_ID`,
  `CES_LOCATION` (default `"us"`), and `CES_APP_ID` (default
  `"shopping-assistant-app-dev"`) env vars on the microservice — see
  `microservice/ces_session_service.py`.
- **Infra prerequisite**: the microservice's *Cloud Run* runtime service
  account needs an IAM grant to call the CES SessionService on the target GCP
  project — this was verified end-to-end against the live dev app using this
  dev machine's own `gcloud` ADC credentials (which already have the needed
  access), but that's a different identity than the Cloud Run default
  Compute Engine service account `microservice/deploy.sh` uses. Confirm the
  correct role (e.g. by checking what the identity running
  `scripts/smoke_test_routing.py`/tested here locally holds via
  `gcloud projects get-iam-policy ecom-cx-agent`) and grant it to the Cloud
  Run SA before deploying the chat proxy — this hasn't been done yet.

### Widget payload shape — confirmed live for the carousel

A live turn against the dev app (`show me some running shoes`) returned:
```json
{"type": "product_detail_carousel", "productDetails": [{"imageUris": [...], "productId": "sku_1029", "subtitle": "Northline · shoes", "price": "$110.49", "title": "TrailBlaze Pro Trail Runner"}, ...]}
```
So the platform injects a `type` field (derived from the tool's `widgetType`)
even though `show_product_carousel.json`'s own params schema doesn't declare
one — `renderWidget()` in `index.html` now dispatches primarily on `type`.
`show_product_comparison`'s and `show_order_summary`'s exact `type` strings
weren't confirmed live (hit a GCP quota limit mid-verification) — those two
still fall back to structural matching (`features` present / `costBreakdown`
present), which is schema-guaranteed regardless of the platform's exact
naming, so it should be safe, but hasn't been exercised against a real
response the way the carousel has.

## `widget-embed.html` — chat-messenger SDK embed (reference/fallback)

The original page, embedding Google's prebuilt `chat-messenger` SDK
(`gstatic.com/chat-messenger/sdk/prod/v1.16/`), pointed at the
`shopping-assistant-app-dev` deployment (`a5ea201d-d892-4594-a986-ec052c289bd5`).
Kept for reference — it's a working, fully-supported integration path, it
just can't render this app's widget tools the way `index.html` does.

```bash
cd web
python3 -m http.server 8000   # then open widget-embed.html
```

Notes on its auth flow:

- The `chat-messenger` SDK always requires an `accessToken` client-side —
  `enable_public_access` alone is not enough; without a token it fails with
  `Error: No access token found.` before any network call is even made (no
  console error, no network entry — the SDK swallows it).
- This page sets `tokenBroker: { enableTokenBroker: true }` in `createContext`,
  which makes the SDK auto-fetch a token itself by POSTing to the deployment's
  public `:generateChatToken` REST endpoint. This only works unauthenticated
  because the deployment's channel profile has `enable_public_access: True`
  (and `enable_recaptcha: False`, so no reCAPTCHA widget is needed either). No
  custom backend or manually-supplied token is required for this dev widget.
- To point this page at a different deployment (e.g. staging/prod), swap the
  `deploymentName` value in the inline `<script>` block — and make sure that
  deployment's channel profile also has `enable_public_access: True`, or the
  token broker will fail the same way.
