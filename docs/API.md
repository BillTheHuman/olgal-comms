# API contract

All `/api/v1` routes require `Authorization: Bearer <capability>`. There is no recipient selector.

| Method | Route | Capability |
| --- | --- | --- |
| GET | `/status` | valid token |
| POST | `/notifications` | `notify_self` |
| POST | `/voice-notes` | `voice_note_self` |
| POST | `/attention` | `request_attention` |
| POST | `/calls` | `request_call_self` |
| GET | `/sessions/{id}` | session owner |
| POST | `/sessions/{id}/end` | session owner |
| POST/GET | `/sessions/{id}/signals` | session owner |

Unknown request fields are rejected. Content limits, transport allowlists, TTL bounds, ownership,
rate limits, and emergency gates are enforced server-side.
