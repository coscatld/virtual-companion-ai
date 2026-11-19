import hmac
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from virtual_lover_agent.app.dialogue import Companion
from virtual_lover_agent.app.http_api import MAX_CHAT_BODY_BYTES, access_token, current_runtime, make_http_app, read_body
from virtual_lover_agent.personal.config import PersonalSettings
from virtual_lover_agent.personal.profile import PersonalProfile, PersonalSettingsStore
from virtual_lover_agent.personal.runtime import PersonalRuntime, open_personal_runtime


def require_personal(
    runtime: Annotated[PersonalRuntime, Depends(current_runtime)],
    token: Annotated[str, Depends(access_token)],
) -> PersonalSettingsStore:
    if not hmac.compare_digest(token.encode("utf-8"), runtime.personal_token.encode("utf-8")):
        raise HTTPException(401, "invalid_token", headers={"WWW-Authenticate": "Bearer"})
    return runtime.personal_settings


async def read_profile(store: PersonalSettingsStore) -> PersonalProfile:
    try:
        return await store.read()
    except (sqlite3.Error, ValidationError) as exc:
        raise HTTPException(503, "profile_unavailable") from exc


async def resolve_companion(store: Annotated[PersonalSettingsStore, Depends(require_personal)]) -> Companion:
    return (await read_profile(store)).companion()


def create_app(settings: PersonalSettings | None = None) -> FastAPI:
    settings = settings or PersonalSettings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with open_personal_runtime(settings) as runtime:
            app.state.runtime = runtime
            yield

    app = make_http_app(
        title="GA Personal Node", mode=settings.mode, http_origins=settings.http_origins,
        auth_configured=True, lifespan=lifespan, resolve_companion=resolve_companion,
    )
    static_path = Path(__file__).resolve().parents[1] / "static"
    app.mount("/static", StaticFiles(directory=static_path, check_dir=False), name="personal-static")

    @app.get("/", include_in_schema=False)
    def personal_ui():
        return FileResponse(static_path / "index.html")

    @app.get("/v1/profile")
    async def personal_profile(store: Annotated[PersonalSettingsStore, Depends(require_personal)]) -> PersonalProfile:
        return await read_profile(store)

    @app.put("/v1/profile", openapi_extra={"requestBody": {"required": True, "content": {
        "application/json": {"schema": PersonalProfile.model_json_schema()},
    }}})
    async def update_profile(
        request: Request, store: Annotated[PersonalSettingsStore, Depends(require_personal)],
    ) -> PersonalProfile:
        raw = await read_body(request, MAX_CHAT_BODY_BYTES + 4096, "profile_too_large")
        try:
            profile = PersonalProfile.model_validate_json(raw)
        except ValidationError as exc:
            raise HTTPException(422, "invalid_profile") from exc
        try:
            await store.update(profile)
        except sqlite3.Error as exc:
            raise HTTPException(503, "profile_unavailable") from exc
        return profile

    return app
