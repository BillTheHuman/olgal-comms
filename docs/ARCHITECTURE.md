# Architecture

```text
AI application
  -> MCP or loopback REST
  -> capability and policy engine
  -> self-only session state + metadata audit
  -> SimpleX notification
  -> iPhone PWA over Tailscale
  -> WebRTC media
       |-> native-audio model
       `-> STT -> text model -> TTS

Optional private call transports: TerminalPhone v2 or local SIP
Disabled future adapters: Apple Messages relay and carrier/PSTN
```

The REST and MCP interfaces intentionally omit a recipient field. A future project that contacts
other people must introduce a separate contact authority and consent model instead of widening
`self` implicitly.

Call state is explicit: `requested`, `notified`, `deferred`, `accepted`, `active`, `declined`,
`expired`, `ended`, or `failed`. Only the owner capability can accept, defer, or decline a request;
the requesting AI cannot make that decision for the owner. A model's claim does not count as
delivery or acceptance. Signal insertion and terminal transitions share one protected database
operation, so an ended or expired call cannot retain a late SDP or ICE record. The Hearth also
releases its microphone tracks and peer connection on explicit hang-up and browser privacy
boundaries.
