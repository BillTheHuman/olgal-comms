# Security Policy

## Supported versions

Only the latest tagged release and the `main` branch receive security fixes during initial
development.

## Reporting

Do not open a public issue containing secrets, working exploits, private addresses, or message
content. Use GitHub's private vulnerability-reporting flow for this repository.

## Security properties

- All AI operations are self-only and capability-scoped.
- The HTTP service binds to loopback unless an operator makes a reviewed change.
- Emergency ringing is disabled by default and requires both a service switch and a separately
  provisioned capability.
- Audit data contains operational metadata, not bodies or audio.
- iMessage and PSTN are unavailable until their explicit legal, credential, and spending gates are
  satisfied.

## Non-guarantees

OlGal Comms does not make Apple, SimpleX, Tor, Tailscale, SIP providers, Venice, browsers, or the
underlying operating system trusted. A process with the same Unix-user privileges may still read
that user's environment, database, or live audio. Device compromise defeats application-level
controls.
