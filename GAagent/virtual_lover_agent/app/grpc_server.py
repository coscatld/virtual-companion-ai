import asyncio
import logging
from typing import AsyncIterator

import grpc
import grpc.aio

import speech_recognition as sr
import edge_tts
import io
import tempfile
import os
import redis.asyncio as aioredis

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


class AudioService(agent_proto_pb2_grpc.AudioServiceServicer):
    
    async def StreamAudioChat(self, request_iterator, context):
        logger.info("[gRPC Audio] Received new audio stream request")
        
        audio_buffer = bytearray()
        user_id = "Anonymous"
        session_id = ""
        system_prompt = "You are a helpful AI assistant."
        
        # 1. 接收来自 Java 前端的二进制音频片段
        try:
            async for request in request_iterator:
                if request.audio_chunk:
                    audio_buffer.extend(request.audio_chunk)
                if request.user_id:
                    user_id = request.user_id
                if request.session_id:
                    session_id = request.session_id
                if request.system_prompt:
                    system_prompt = request.system_prompt
        except Exception as e:
            logger.error(f"[gRPC Audio] Read stream error: {e}")
            return
            
        if not audio_buffer:
            logger.warning("[gRPC Audio] Empty audio buffer received.")
            return

        logger.info(f"[gRPC Audio] Finished receiving {len(audio_buffer)} bytes from {user_id}. Running ASR...")

        # 2. 语音识别 (ASR)
        recognized_text = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                tmp_wav.write(audio_buffer)
                tmp_name = tmp_wav.name
                
            recognizer = sr.Recognizer()
            with sr.AudioFile(tmp_name) as source:
                audio_data = recognizer.record(source)
                recognized_text = recognizer.recognize_google(audio_data, language="zh-CN")
            
            os.remove(tmp_name)
            logger.info(f"[gRPC Audio] User said: {recognized_text}")
        except sr.UnknownValueError:
            logger.warning("[gRPC Audio] ASR could not understand audio")
            recognized_text = "..." 
        except Exception as e:
            logger.error(f"[gRPC Audio] ASR error: {e}")
            recognized_text = "你好" 

        # 3. 获取 Redis 历史记忆 (短期记忆)
        REDIS_HOST = os.getenv("redis_host", "localhost")
        REDIS_PORT = int(os.getenv("redis_port", "6379"))
        HISTORY_CACHE_KEY = f"vr:history:{user_id}"
        
        redis_client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        recent_history = []
        try:
            recent_history = await redis_client.lrange(HISTORY_CACHE_KEY, 0, 9)
            recent_history.reverse()
        except Exception as e:
            logger.error(f"[gRPC Audio] Redis error: {e}")
            
        user_message_with_history = ""
        if recent_history:
            user_message_with_history += "<Chat_History>\n" + "\n".join(recent_history) + "\n</Chat_History>\n\n"
        user_message_with_history += f"Current User Query: {recognized_text}"
        
        # 4. LLM 推理
        messages = [
            ("system", system_prompt),
            ("user", user_message_with_history)
        ]
        
        ai_reply_text = ""
        try:
            response = await agent_graph.ainvoke({"messages": messages})
            ai_reply_text = response["messages"][-1].content
            logger.info(f"[gRPC Audio] AI Response: {ai_reply_text}")
        except Exception as e:
            logger.error(f"[gRPC Audio] LLM error: {e}")
            ai_reply_text = "对不起，我遇到了一点问题。"

        # 异步存入本轮回复到 Redis 短期记忆
        if recognized_text.strip() and recognized_text != "...":
            try:
                await redis_client.rpush(HISTORY_CACHE_KEY, f"User: {recognized_text}", f"AI: {ai_reply_text}")
                await redis_client.ltrim(HISTORY_CACHE_KEY, -50, -1)
                await redis_client.expire(HISTORY_CACHE_KEY, 3600)
            except:
                pass
        
        await redis_client.aclose()

        # 5. 语音合成 (TTS)
        voice = "zh-CN-XiaoxiaoNeural"
        communicator = edge_tts.Communicate(ai_reply_text, voice)
        
        tts_buffer = bytearray()
        try:
            async for chunk in communicator.stream():
                if chunk["type"] == "audio":
                    tts_buffer.extend(chunk["data"])
        except Exception as e:
            logger.error(f"[gRPC Audio] TTS error: {e}")
        
        # 拆分发送回 Java，防止包太大
        chunk_size = 32000
        for i in range(0, len(tts_buffer), chunk_size):
            yield agent_proto_pb2.AudioResponse(
                ai_audio_chunk=bytes(tts_buffer[i:i+chunk_size]),
                ai_text=ai_reply_text if i == 0 else "" 
            )
            
        logger.info("[gRPC Audio] Response Sent.")

async def serve():
    """
    启动 async gRPC Server (grpc.aio)
    """
    server = grpc.aio.server()

    # 关键：使用生成的 add_*_to_server 函数注册服务
    # 这会正确地把 chatStream 方法用 Protobuf 序列化器绑定到 gRPC server
    agent_proto_pb2_grpc.add_AgentServiceServicer_to_server(AgentService(), server)
    agent_proto_pb2_grpc.add_AudioServiceServicer_to_server(AudioService(), server)

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

