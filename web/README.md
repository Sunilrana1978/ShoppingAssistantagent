# Web Widget Test Page

Standalone local test page embedding the deployed CXAS web widget via Google's
`chat-messenger` SDK, pointed at the `shopping-assistant-app-dev` deployment
(`a5ea201d-d892-4594-a986-ec052c289bd5`).

## Run locally

```bash
cd web
python3 -m http.server 8000
```

Then open http://localhost:8000 in a browser.

## Notes

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
- This page is static — no build step, no dependencies.
