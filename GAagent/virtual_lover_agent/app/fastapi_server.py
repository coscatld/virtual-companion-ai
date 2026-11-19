"""Compatibility factory and ASGI application for older entry points."""

from typing import TYPE_CHECKING

from fastapi import FastAPI

from virtual_lover_agent.app.config import Settings

if TYPE_CHECKING:
    from virtual_lover_agent.enterprise.config import EnterpriseSettings
    from virtual_lover_agent.personal.config import PersonalSettings


def create_app(
    settings: "EnterpriseSettings | PersonalSettings | None" = None, *, serve_grpc: bool = False,
) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.mode == "personal":
        from virtual_lover_agent.personal.http_server import create_app as create_personal_app

        return create_personal_app(settings)

    from virtual_lover_agent.enterprise.http_server import create_app as create_enterprise_app

    return create_enterprise_app(settings, serve_grpc=serve_grpc)


def __getattr__(name: str):
    if name == "app":
        asgi = create_app()
        globals()["app"] = asgi
        return asgi
    raise AttributeError(name)
