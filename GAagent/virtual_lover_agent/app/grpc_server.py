import asyncio
import logging
from typing import AsyncIterator

import grpc
import grpc.aio

from virtual_lover_agent.protos import agent_proto_pb2
from virtual_lover_agent.protos import agent_proto_pb2_grpc
from virtual_lover_agent.agent.graph.gragh01 import agent_graph

logger = logging.getLogger(__name__)


class AgentService(agent_proto_pb2_grpc.AgentServiceServicer):
    """
    Python gRPC Server 实现类，继承自生成的 AgentServiceServicer。
    chatStream 是 server-side streaming RPC: 接收一个请求，不断 yield ChatResponse。
    """

    async def chatStream(
        self,
        request: agent_proto_pb2.ChatRequest,
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[agent_proto_pb2.ChatResponse]:
        """
        gRPC 流式处理接口：接收单个 ChatRequest，源源不断地产出 ChatResponse 给 Java 后端
        """
        logger.info(f"📨 [gRPC] Received request from User: {request.user_id}")

        user_message = request.user_message
        system_prompt = request.system_prompt

        # 组装送到 LangGraph 的 Messages 格式
        messages = [
            ("system", system_prompt),
            ("user", user_message)
        ]

        try:
            async for event in agent_graph.astream_events(
                {"messages": messages},
                version="v2"
            ):
                kind = event["event"]
                # 过滤出聊天模型正在生成文字的事件
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        yield agent_proto_pb2.ChatResponse(
                            delta=chunk,
                            emotion="normal",
                            is_end=False
                        )
                elif kind == "on_tool_start":
                    yield agent_proto_pb2.ChatResponse(
                        delta=f"\n[AI思考中: 调用工具 {event['name']}]\n",
                        emotion="thinking",
                        is_end=False
                    )

            # 模型执行完毕，发送结束标志
            yield agent_proto_pb2.ChatResponse(
                delta="",
                emotion="done",
                is_end=True
            )

        except Exception as e:
            logger.error(f"Error during graph execution: {e}", exc_info=True)
            yield agent_proto_pb2.ChatResponse(
                delta=f"\n[系统内部错误: {str(e)}]",
                emotion="error",
                is_end=True
            )


async def serve():
    """
    启动 async gRPC Server (grpc.aio)
    """
    server = grpc.aio.server()

    # 关键：使用生成的 add_*_to_server 函数注册服务
    # 这会正确地把 chatStream 方法用 Protobuf 序列化器绑定到 gRPC server
    agent_proto_pb2_grpc.add_AgentServiceServicer_to_server(AgentService(), server)

    listen_addr = '[::]:7000'
    server.add_insecure_port(listen_addr)

    logger.info(f"🚀 Python AI gRPC Server starting on {listen_addr}")
    await server.start()
    logger.info(f"✅ Python AI gRPC Server is ready to accept connections on port 7000")

    # 阻塞直到停止信号
    await server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(serve())

