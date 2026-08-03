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

- The deployment's channel profile has `enable_public_access: True`, so the
  widget works with no `accessToken` — the commented-out `accessToken` block
  in `index.html` is inactive and left only as a reference for switching to a
  token-based flow later.
- To point this page at a different deployment (e.g. staging/prod), swap the
  `deploymentName` value in the inline `<script>` block.
- This page is static — no build step, no dependencies.
