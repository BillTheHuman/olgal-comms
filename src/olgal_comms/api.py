from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .config import Settings
from .models import Capability, Priority, SessionState
from .policy import PolicyDenied
from .service import CommsService
from .store import SignalUnavailable

HEARTH_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; connect-src 'self'; img-src 'self'; style-src 'self'; "
    "script-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; "
    "frame-ancestors 'none'"
)


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NotifyRequest(StrictRequest):
    text: str = Field(min_length=1, max_length=4000)
    priority: Priority = Priority.ROUTINE


class SessionRequest(StrictRequest):
    reason: str = Field(min_length=1, max_length=1000)
    priority: Priority = Priority.IMPORTANT
    ttl: int = Field(default=300, ge=30, le=3600)


class CallRequest(SessionRequest):
    transport: Literal["terminalphone", "sip", "webrtc"] = "webrtc"
    media_mode: Literal["text-voice", "native-audio"] = "text-voice"


class TransitionRequest(StrictRequest):
    state: Literal["accepted", "deferred", "declined"]


class SignalRequest(StrictRequest):
    payload: dict[str, Any]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    service = CommsService(settings)
    app = FastAPI(title="OlGal Comms", version="0.2.0", docs_url="/api/docs")
    app.state.service = service

    def capability(authorization: str | None = Header(default=None)) -> Capability:
        token = authorization.removeprefix("Bearer ") if authorization else None
        try:
            return service.policy.authenticate(token)
        except PolicyDenied as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @app.exception_handler(PolicyDenied)
    async def policy_denied(_request, exc: PolicyDenied):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.get("/api/v1/status")
    def status(_cap: Capability = Depends(capability)):
        return service.status()

    @app.post("/api/v1/notifications")
    def notify(body: NotifyRequest, cap: Capability = Depends(capability)):
        return service.notify(cap, body.text, body.priority)

    @app.post("/api/v1/voice-notes")
    def voice_note(body: NotifyRequest, cap: Capability = Depends(capability)):
        return service.voice_note(cap, body.text, body.priority)

    @app.post("/api/v1/attention")
    def request_attention(body: SessionRequest, cap: Capability = Depends(capability)):
        return service.request_session(
            cap, "attention", body.reason, body.priority, body.ttl, "simplex"
        ).public()

    @app.post("/api/v1/calls")
    def request_call(body: CallRequest, cap: Capability = Depends(capability)):
        return service.request_session(
            cap,
            "call",
            body.reason,
            body.priority,
            body.ttl,
            body.transport,
            body.media_mode,
        ).public()

    @app.get("/api/v1/inbox")
    def inbox(response: Response, cap: Capability = Depends(capability)):
        response.headers["Cache-Control"] = "no-store"
        return {
            "sessions": [
                session.owner_summary() for session in service.list_owner_sessions(cap, 50)
            ]
        }

    @app.get("/api/v1/sessions/{session_id}")
    def get_session(session_id: str, cap: Capability = Depends(capability)):
        return service.get_session(cap, session_id).public()

    @app.post("/api/v1/sessions/{session_id}/end")
    def end_session(session_id: str, cap: Capability = Depends(capability)):
        try:
            return service.end_session(cap, session_id).public()
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/v1/sessions/{session_id}/transition")
    def transition(session_id: str, body: TransitionRequest, cap: Capability = Depends(capability)):
        try:
            return service.owner_decide(cap, session_id, SessionState(body.state)).public()
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/v1/sessions/{session_id}/signals")
    def add_signal(session_id: str, body: SignalRequest, cap: Capability = Depends(capability)):
        try:
            signal_id = service.add_signal(cap, session_id, body.payload)
        except SignalUnavailable as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        return {"id": signal_id, "accepted": True}

    @app.get("/api/v1/sessions/{session_id}/signals")
    def get_signals(
        session_id: str,
        after: int = 0,
        limit: int = 100,
        cap: Capability = Depends(capability),
    ):
        if after < 0:
            raise HTTPException(status_code=422, detail="after must be non-negative")
        service.signaling_session(cap, session_id)
        return {"signals": service.store.signals(session_id, after, max(1, min(limit, 100)))}

    web_root = Path(os.getenv("OLGAL_WEB_ROOT", Path(__file__).parents[2] / "web"))
    if web_root.exists():
        app.mount("/assets", StaticFiles(directory=web_root), name="assets")

        @app.get("/sw.js", include_in_schema=False)
        def service_worker():
            return FileResponse(web_root / "sw.js", media_type="text/javascript")

        @app.get("/manifest.webmanifest", include_in_schema=False)
        def manifest():
            return FileResponse(
                web_root / "manifest.webmanifest", media_type="application/manifest+json"
            )

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(
                web_root / "index.html",
                headers={
                    "Content-Security-Policy": HEARTH_CONTENT_SECURITY_POLICY,
                    "X-Frame-Options": "DENY",
                },
            )

    return app


app = create_app()


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run("olgal_comms.api:app", host=settings.bind_host, port=settings.bind_port)


if __name__ == "__main__":
    main()
