"""Compatibility launcher for the old combined HTTP/gRPC process."""

import argparse
import asyncio
import os

import uvicorn

from virtual_lover_agent.app.config import Settings
from virtual_lover_agent.app.fastapi_server import create_app
from virtual_lover_agent.personal.cli import main as personal_main
from virtual_lover_agent.personal.profile import PersonalSettingsStore


def main(*, default_mode: str = "enterprise") -> None:
    parser = argparse.ArgumentParser(description="Run the GA companion server.")
    parser.add_argument("command", choices=("serve", "token"), nargs="?", default="serve")
    parser.add_argument("--mode", choices=("personal", "enterprise"))
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    try:
        settings = Settings.from_env(default_mode=default_mode, mode=args.mode)
    except ValueError as exc:
        parser.error(str(exc))
    if args.command == "token":
        if settings.mode != "personal":
            parser.error("token requires personal mode")
        print(asyncio.run(PersonalSettingsStore(settings).initialize()))
        return

    host = settings.http_host if settings.mode == "personal" else os.getenv("GA_HTTP_HOST", "127.0.0.1")
    port = settings.http_port if settings.mode == "personal" else int(os.getenv("GA_HTTP_PORT", "8081"))
    uvicorn.run(
        create_app(settings, serve_grpc=settings.mode == "enterprise"),
        host=args.host or host,
        port=args.port if args.port is not None else port,
    )


if __name__ == "__main__":
    main()
