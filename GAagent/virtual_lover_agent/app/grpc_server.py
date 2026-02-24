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

    async def StreamAudioChat(self, request_iterator, context) -> AsyncIterator[agent_proto_pb2.AudioResponse]:
        logger.info("[gRPC Audio] 🎧 New audio stream connected from Java Gateway")
        #初始化变量
        audio_buffer = bytearray()
        user_id = "Anonymous"
        session_id = ""
        system_prompt = "You are a helpful AI assistant."

        try:
            async for request in request_iterator:
                # 1. 接收基础信息
                if request.user_id: user_id = request.user_id
                if request.session_id: session_id = request.session_id
                if request.system_prompt: system_prompt = request.system_prompt

                # 2. 累加音频数据
                if request.audio_chunk:
                    audio_buffer.extend(request.audio_chunk)
                else:
                    #收到0字节包,代表用户这段话说完了
                    if not audio_buffer:
                        continue

                    logger.info(f"[{user_id}]  Received EOF (0 byte). Starting Inference Pipeline...")

                    # --- 阶段 A：无落盘 + 防阻塞的 ASR ---
                    recognized_text = await self._async_asr(audio_buffer)
                    logger.info(f"[{user_id}] 🗣️ User said: {recognized_text}")

                    if not recognized_text.strip() or recognized_text == "...":
                        audio_buffer.clear()
                        continue  # 没听清，忽略本次，继续等下一句

                    # --- 阶段 B：极速获取记忆 ---
                    messages = await self._build_prompt_with_history(user_id, system_prompt, recognized_text)

                    # --- 阶段 C：大模型流式推理 + TTS 实时合成 (边想边读) ---
                    full_reply = ""
                    # 使用 async for 消费这个双轨生成器
                    async for audio_response, text_chunk in self._stream_llm_and_tts(messages):
                        if text_chunk:
                            # 1. 把零碎的文字拼起来，留着最后存 Redis 用
                            full_reply += text_chunk
                        if audio_response:
                            # 2. 如果这回合生成了音频，立刻 yield 给 Java！
                            yield audio_response

                    # --- 阶段 D：后台静默存入记忆 (不阻塞返回) ---
                    asyncio.create_task(self._save_history_async(user_id, recognized_text, full_reply))

                    # 准备就绪，清空 buffer，倾听用户的下一句话
                    audio_buffer.clear()
                    logger.info(f"[{user_id}] ✅ Round complete. Listening for next sentence...")

        except Exception as e:
            logger.error(f"[gRPC Audio] Stream interrupted: {e}")

    # ==================== 核心功能组件提取 ====================

    async def _async_asr(self, audio_bytes: bytearray) -> str:
        """异步、无磁盘 IO 的语音识别"""

        def run_asr():
            try:
                # 核心优化 1：使用 BytesIO 替代 tempfile，纯内存操作
                wav_io = io.BytesIO(audio_bytes)
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_io) as source:
                    audio_data = recognizer.record(source)
                    return recognizer.recognize_google(audio_data, language="zh-CN")
            except sr.UnknownValueError:
                return "..."
            except Exception as e:
                logger.error(f"ASR error: {e}")
                return "你好"

        # 核心优化 2：将同步的第三方库推入线程池，绝不卡死主事件循环
        return await asyncio.to_thread(run_asr)

    async def _build_prompt_with_history(self, user_id: str, system_prompt: str, user_text: str) -> list:
        """获取 Redis 短期记忆并组装消息"""
        REDIS_HOST = os.getenv("redis_host", "localhost")
        REDIS_PORT = int(os.getenv("redis_port", "6379"))
        HISTORY_KEY = f"vr:history:{user_id}"

        redis_client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        try:
            recent_history = await redis_client.lrange(HISTORY_KEY, 0, 9)
            recent_history.reverse()
        except Exception:
            recent_history = []
        finally:
            await redis_client.aclose()

        history_str = "<Chat_History>\n" + "\n".join(recent_history) + "\n</Chat_History>\n\n" if recent_history else ""
        user_message = f"{history_str}Current User Query: {user_text}"

        return [("system", system_prompt), ("user", user_message)]

    async def _stream_llm_and_tts(self, messages: list):
        """核心优化 3：大模型流式输出 -> 标点符号截断 -> 实时分块 TTS 合成"""
        current_sentence = ""
        punctuation_marks = {'。', '！', '？', '，', '；', '\n', '.', '!', '?', ',', ';'}

        try:
            # 使用 astream_events 捕获 LLM 流式输出
            async for event in agent_graph.astream_events({"messages": messages}, version="v2"):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if not chunk: continue

                    current_sentence += chunk

                    # 🚀 亮点：只要大模型吐出文字，立刻抛给外层去拼装全量文本，音频位给 None
                    yield (None, chunk)

                    # 探测到句子边界（标点符号）
                    if any(p in chunk for p in punctuation_marks):
                        sentence_to_speak = current_sentence.strip()
                        current_sentence = ""  # 立即清空，开始收集下一句

                        if sentence_to_speak:
                            # 开启 TTS 并在内部通过 yield 逐块传回
                            async for audio_chunk in self._generate_tts_stream(sentence_to_speak):
                                # 🚀 抛出生成的音频块，文本位给空字符串
                                yield (audio_chunk, "")

            # 处理结尾没有标点符号的剩余文字
            if current_sentence.strip():
                async for audio_chunk in self._generate_tts_stream(current_sentence.strip()):
                    yield (audio_chunk, "")

        except Exception as e:
            logger.error(f"LLM/TTS Pipeline Error: {e}")

    async def _generate_tts_stream(self, text: str) -> AsyncIterator[agent_proto_pb2.AudioResponse]:
        """调用 Edge TTS 将一小段文本转为语音流"""
        communicator = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
        is_first_chunk = True

        try:
            async for chunk in communicator.stream():
                if chunk["type"] == "audio":
                    # 只在第一个音频块附带文本，用于前端字幕展示
                    yield agent_proto_pb2.AudioResponse(
                        ai_audio_chunk=chunk["data"],
                        ai_text=text if is_first_chunk else ""
                    )
                    is_first_chunk = False
        except Exception as e:
            logger.error(f"TTS Synthesis error: {e}")

    async def _save_history_async(self, user_id: str, user_text: str, ai_text: str):
        """核心优化 4：异步后台落库，不阻塞下一轮对话"""
        if not user_text.strip() or not ai_text.strip(): return

        REDIS_HOST = os.getenv("redis_host", "localhost")
        REDIS_PORT = int(os.getenv("redis_port", "6379"))
        HISTORY_KEY = f"vr:history:{user_id}"

        try:
            redis_client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            await redis_client.rpush(HISTORY_KEY, f"User: {user_text}", f"AI: {ai_text}")
            await redis_client.ltrim(HISTORY_KEY, -50, -1)
            await redis_client.expire(HISTORY_KEY, 3600)
            await redis_client.aclose()
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

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

