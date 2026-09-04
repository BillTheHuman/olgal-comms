# Deployment on OlGal

## Service

1. Create a virtual environment and install the package.
2. Generate distinct AI and owner-browser tokens without printing them:
   `olgal-comms-token trusted-ai --store ~/.config/olgal-comms/tokens.json --token-output ~/.config/olgal-comms/ai.token`
   and `olgal-comms-token owner-iphone --owner-browser --store ~/.config/olgal-comms/tokens.json --token-output ~/.config/olgal-comms/browser.token`.
3. Store `OLGAL_TOKENS_JSON` using a root-readable systemd credential or an environment file with
   mode `0600`; never commit it.
4. Copy and review `deploy/systemd/olgal-comms.service`, replacing the example paths and user.
5. Confirm the service listens only on `127.0.0.1:8791`.

## Existing Caddy/Tailscale path

OlGal currently routes `https://olgal.tailb53d24.ts.net/` through Tailscale Serve to Caddy on port
38080. Merge the example in `deploy/caddy/olgal-comms.Caddyfile` into `/etc/caddy/Caddyfile` before
the existing catch-all proxy. Validate and reload Caddy; do not overwrite the existing route.

The current Tailscale health check reports a DNS configuration fetch failure. Resolve that warning
and verify the tailnet hostname from the iPhone before treating PWA installation as complete.

## iPhone

Open `https://olgal.tailb53d24.ts.net/comms/` in Safari while connected to the tailnet, choose Add to
Home Screen, enter the owner's PWA capability token, and test microphone permission. Use a separate
low-privilege token for the browser; do not reuse an AI token.
