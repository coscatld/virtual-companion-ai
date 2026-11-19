import argparse
import asyncio

import uvicorn

from virtual_lover_agent.personal.config import PersonalSettings
from virtual_lover_agent.personal.http_server import create_app
from virtual_lover_agent.personal.profile import PersonalSettingsStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the GA personal companion.")
    parser.add_argument("command", choices=("serve", "token"), nargs="?", default="serve")
    parser.add_argument("--mode", choices=("personal",), help=argparse.SUPPRESS)
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    try:
        settings = PersonalSettings.from_env()
    except ValueError as exc:
        parser.error(str(exc))
    if args.command == "token":
        print(asyncio.run(PersonalSettingsStore(settings).initialize()))
        return
    uvicorn.run(
        create_app(settings),
        host=args.host or settings.http_host,
        port=args.port if args.port is not None else settings.http_port,
    )
