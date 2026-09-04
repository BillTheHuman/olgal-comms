---
name: olgal-comms
description: Use the owner's private OlGal communication service to check availability, send a self-only message or voice note, request attention, or request and manage a private call. Use when the user explicitly asks an AI application to contact them through OlGal; do not use for contacting anyone else.
---

# OlGal Comms

Use the `olgal-comms` MCP tools. Start with `comms_status` when readiness matters.

- Every action addresses the configured owner. Never add or infer another recipient.
- Keep queued, notified, delivered, accepted, and active states distinct.
- Do not retry rejected, expired, rate-limited, or unavailable requests automatically.
- Ordinary calls require consent. Emergency direct ringing is disabled unless separately enabled
  and provisioned by the owner.
- Do not expose credentials, message bodies, phone numbers, Apple IDs, or contact addresses.
