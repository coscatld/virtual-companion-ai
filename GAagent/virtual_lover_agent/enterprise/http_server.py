from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

from virtual_lover_agent.app.config import http_origins
from virtual_lover_agent.app.dialogue import Companion
from virtual_lover_agent.app.http_api import access_token, current_runtime, make_http_app
from virtual_lover_agent.app.runtime import Runtime
from virtual_lover_agent.enterprise.config import EnterpriseSettings
from virtual_lover_agent.enterprise.runtime import open_enterprise_runtime


class GatewayCompanion(BaseModel):
    userId: str = Field(min_length=1)
    companionId: str = "default"
    systemPrompt: str | None = None
    voiceId: str | None = None


def create_app(settings: EnterpriseSettings | None = None, *, serve_grpc: bool = False) -> FastAPI:
    """HTTP facade for older mobile clients that delegate identity to Spring Boot."""
    settings = settings or EnterpriseSettings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with open_enterprise_runtime(settings) as runtime:
            app.state.runtime = runtime
            if not serve_grpc:
                yield
                return

            from virtual_lover_agent.enterprise.grpc_server import start_grpc

            server = await start_grpc(runtime, settings)
            try:
                yield
            finally:
                await server.stop(3)

    async def resolve_companion(
        runtime: Annotated[Runtime, Depends(current_runtime)],
        token: Annotated[str, Depends(access_token)],
    ) -> Companion:
        if not settings.internal_token:
            raise HTTPException(503, "mobile_auth_unavailable")
        try:
            response = await runtime.http.get(
                f"{settings.gateway_url}/internal/mobile/companion",
                headers={"Authorization": f"Bearer {token}", "X-GA-Internal-Token": settings.internal_token},
                timeout=8,
            )
            if response.status_code == 401:
                raise HTTPException(401, "invalid_token", headers={"WWW-Authenticate": "Bearer"})
            if response.status_code == 404:
                raise HTTPException(404, "companion_not_found")
            response.raise_for_status()
            profile = GatewayCompanion.model_validate_json(response.content)
        except (httpx.HTTPError, ValidationError) as exc:
            raise HTTPException(503, "mobile_auth_unavailable") from exc
        return Companion(profile.userId, profile.companionId or "default", profile.systemPrompt or "", profile.voiceId or "")

    return make_http_app(
        title="GA Enterprise Mobile API", mode=settings.mode, http_origins=http_origins(),
        auth_configured=bool(settings.internal_token), lifespan=lifespan, resolve_companion=resolve_companion,
    )
