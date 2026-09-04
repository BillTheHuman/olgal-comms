---
name: olgal-comms
description: Use the owner's private OlGal communication service to check availability, send a self-only message or voice note, request attention, or request and manage a private call. Use when the user explicitly asks an AI application to contact them through OlGal; do not use for contacting anyone else.
---

# OlGal Comms

Use the `olgal-comms` MCP tools. Start with `comms_status` when transport readiness matters.

- All tools address the configured owner. Never attempt to add or infer another recipient.
- Treat `queued`, `notified`, `delivered`, `accepted`, and `active` as distinct facts. Never claim
  the owner read, heard, or understood a message unless the service explicitly establishes it.
- Use `routine` for ordinary updates, `important` when timely attention helps, and `urgent` only for
  a concrete time-sensitive reason. Emergency direct ringing is unavailable unless the owner has
  separately enabled and provisioned it.
- Use `comms_request_attention` before an ordinary call, then poll only until the returned TTL.
- Do not retry a rejected, expired, rate-limited, or unavailable request automatically.
- Do not place credentials, private message bodies, phone numbers, Apple IDs, or contact addresses
  in logs or tool explanations.
- iMessage and cellular/PSTN are future adapters. A status response saying unavailable is a real
  boundary, not permission to work around it.
