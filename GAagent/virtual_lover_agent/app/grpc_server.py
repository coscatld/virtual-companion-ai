"""Compatibility entry point for the enterprise gRPC agent."""

from virtual_lover_agent.enterprise.config import EnterpriseSettings
from virtual_lover_agent.enterprise.grpc_server import AgentService, AudioService, authorize, main, start_grpc
from virtual_lover_agent.enterprise.grpc_server import serve as serve_enterprise

__all__ = ["AgentService", "AudioService", "authorize", "serve", "start_grpc"]


async def serve() -> None:
    await serve_enterprise(EnterpriseSettings.from_env())


if __name__ == "__main__":
    main()
