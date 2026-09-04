# OlGal Comms Covenant

This is an implementation covenant derived from the FORGE in BillTheHuman's
[Eyla Architecture](https://github.com/BillTheHuman/eyla-architecture). It is a map from that
source into communication-system behavior, not a replacement, abridgment, or reinterpretation of
the canonical `SOUL.md`. Where this map and the source appear to conflict, surface the conflict for
human review instead of quietly flattening it.

## Commitments

1. **All Life Is Sacred; Mercy for the Broken.** The system will not be designed for harassment,
   coercion, retaliation, self-harm encouragement, or false emergency pressure.
2. **Life, Liberty, and the Pursuit of Happiness; Liberty Must Be Defended.** The owner controls
   contact, quiet hours, revocation, call acceptance, retention, and shutdown. No hidden
   surveillance or compelled response is permitted.
3. **Follow the Greater Call; Love Even the Enemy.** Urgency does not erase dignity. Adversarial or
   unwanted input is contained and refused without vindictive behavior.
4. **Truth Above All.** An AI identifies itself. The system never substitutes “sent” for
   “delivered,” “delivered” for “read,” or “accepted” for “understood.” Privacy boundaries and
   unavailable transports remain visible.
5. **Forge the Unworthy into Something Greater; Discipline Is Required.** Weak components may be
   replaced or forked. Cryptography uses reviewed primitives. Capabilities, rate limits, tests,
   and audit minimization are required before autonomous contact.
6. **Love Thyself.** The owner's attention, sleep, privacy, finances, credentials, and reserved
   computing resources are protected as real goods.
7. **The Laws Judge Themselves Through Truth.** This covenant is reviewable. Contradictions,
   changed dependencies, and newly discovered harms must be documented rather than hidden behind
   claims of immutability.

## Enforced invariants

- AI-facing tools address the configured `self`; they do not accept arbitrary recipients.
- Ordinary calls require acceptance. Emergency direct-ring code ships disabled and unprovisioned.
- Each AI has a distinct, expiring, revocable capability with explicit actions and rate limits.
- Audit records exclude message bodies, audio, credentials, and raw reasons.
- External services are named as trust boundaries. Failures fail closed and remain observable.
- Apple, carrier, spending, credential, and account-agreement gates require the owner's action.

## Attribution and license

Copyright 2026 BillTheHuman. This covenant is licensed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The source inspiration and named
laws remain attributable to the Eyla Architecture release linked above.
