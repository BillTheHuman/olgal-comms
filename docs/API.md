# API contract

All `/api/v1` routes require `Authorization: Bearer <capability>`. There is no recipient selector.

| Method | Route | Capability |
| --- | --- | --- |
| GET | `/status` | valid token |
| POST | `/notifications` | `notify_self` |
| POST | `/voice-notes` | `voice_note_self` |
| POST | `/attention` | `request_attention` |
| POST | `/calls` | `request_call_self` |
| GET | `/inbox` | `manage_self_sessions` |
| GET | `/sessions/{id}` | session owner |
| POST | `/sessions/{id}/transition` | `manage_self_sessions` |
| POST | `/sessions/{id}/end` | session owner or `manage_self_sessions` |
| POST/GET | `/sessions/{id}/signals` | accepted call participant |

Unknown request fields are rejected. Content limits, transport allowlists, TTL bounds, ownership,
rate limits, and emergency gates are enforced server-side. The inbox is a bounded, non-cacheable
snapshot that excludes reasons, reason digests, signal payloads, and technical transport details.
Signal roles are derived from the authenticated capability rather than accepted from clients.
Signal writes are accepted only while the same atomic database operation can confirm an unexpired,
accepted or active call.
