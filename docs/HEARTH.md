# OlGal Hearth direction

OlGal Hearth is the owner-facing shape of OlGal Comms. It should feel like a private household
switchboard rather than an API console.

The selected visual direction is the
[Quiet Switchboard reference](assets/hearth-quiet-switchboard-reference.webp), with the current
[browser implementation](assets/olgal-hearth-preview.webp) kept beside it for an honest,
source-to-build record.

## Locked product principles

- Lead with identity, intent, consent, and honest state.
- Keep connection keys, session identifiers, adapters, and transport details out of the daily
  experience; place the minimum necessary setup under Settings.
- Let requests wait without manufactured urgency. “Later” is a real `deferred` state, not a quiet
  decline or a false delivery status.
- Keep microphone control visible and literal: End call, hidden-page privacy cleanup, revoked
  access, and vanished sessions all release local media tracks and close the peer connection.
- Use distinct, owner-configured identities for trusted AI applications. Never trust caller HTML or
  caller-selected recipients.
- Treat voice letters as an asynchronous, non-demanding form. Until its transport exists, the live
  interface must show an honest empty state rather than invented correspondence.
- Preserve the FORGE-derived covenant as a policy source without treating this interface as a
  replacement for the canonical `SOUL.md`.

## Next additions

1. A local communications simulator for consent, failure, replay, quiet-hours, and voice handoff
   testing without contacting anyone or spending money.
2. Owner-managed AI identity cards: name, recognizable mark, voice, permissions, quiet-hours, and
   revocation.
3. Real voice-letter persistence and playback after the SimpleX transport is paired.

These additions must retain the self-only recipient boundary and require separate gates for Apple,
carrier, credential, spending, or third-party contact authority.
