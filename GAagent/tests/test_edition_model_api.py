import asyncio
import json
import os
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import IsolatedAsyncioTestCase, TestCase, skipIf
from unittest.mock import patch

try:
    from fakeredis import FakeAsyncRedis
except ImportError:
    FakeAsyncRedis = None

from virtual_lover_agent.enterprise.config import EnterpriseSettings
from virtual_lover_agent.personal.config import PersonalSettings

NO_DOTENV = {"PYTHON_DOTENV_DISABLED": "1"}
ENTERPRISE_API = {
    "GA_ENTERPRISE_LLM_BASE_URL": "https://enterprise-models.example.test/v1",
    "GA_ENTERPRISE_LLM_MODEL": "enterprise-chat",
    "GA_ENTERPRISE_LLM_API_KEY": "test-enterprise-key",
}


class EditionModelSettingsTests(TestCase):
    def test_enterprise_does_not_inherit_personal_model_or_mock_mode(self):
        env = {
            **NO_DOTENV,
            "GA_LLM_PROVIDER": "mock",
            "GA_LLM_BASE_URL": "http://127.0.0.1:11434/v1",
            "GA_LLM_MODEL": "personal-model",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(ValueError, "GA_ENTERPRISE_LLM_BASE_URL"):
                EnterpriseSettings.from_env()

    def test_enterprise_requires_a_model_for_configured_api(self):
        env = {
            **NO_DOTENV,
            "GA_ENTERPRISE_LLM_BASE_URL": ENTERPRISE_API["GA_ENTERPRISE_LLM_BASE_URL"],
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(ValueError, "GA_ENTERPRISE_LLM_MODEL"):
                EnterpriseSettings.from_env()

    def test_enterprise_summary_stays_on_its_api_and_keeps_credentials_scoped(self):
        env = {
            **NO_DOTENV,
            **ENTERPRISE_API,
            "GA_SUMMARY_BASE_URL": "http://localhost:8000/v1",
            "GA_SUMMARY_API_KEY": "test-personal-key",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = EnterpriseSettings.from_env()
            self.assertEqual(settings.summary, settings.llm)
            os.environ["GA_ENTERPRISE_SUMMARY_BASE_URL"] = "https://summary.example.test/v1"
            os.environ["GA_ENTERPRISE_SUMMARY_MODEL"] = "enterprise-summary"
            alternate = EnterpriseSettings.from_env().summary

        self.assertEqual(alternate.base_url, "https://summary.example.test/v1")
        self.assertEqual(alternate.model, "enterprise-summary")
        self.assertEqual(alternate.api_key, "")

    def test_personal_defaults_and_overrides_remain_local_and_independent(self):
        with patch.dict(os.environ, {**NO_DOTENV, **ENTERPRISE_API, "GA_DATA_DIR": os.curdir}, clear=True):
            defaults = PersonalSettings.from_env()
            self.assertEqual(defaults.llm.base_url, "http://127.0.0.1:8000/v1")
            self.assertEqual(defaults.llm.api_key, "")
            os.environ["GA_LLM_BASE_URL"] = "http://127.0.0.1:11434/v1"
            os.environ["GA_LLM_MODEL"] = "qwen2.5:7b"
            configured = PersonalSettings.from_env()

        self.assertEqual(configured.llm.base_url, "http://127.0.0.1:11434/v1")
        self.assertEqual(configured.llm.model, "qwen2.5:7b")
        self.assertEqual(configured.summary, configured.llm)


@skipIf(FakeAsyncRedis is None, "Install fakeredis to test the enterprise API integration")
class EnterpriseModelApiTests(IsolatedAsyncioTestCase):
    async def test_enterprise_chat_and_summary_call_their_configured_apis(self):
        import grpc

        from virtual_lover_agent.enterprise.grpc_server import AgentService
        from virtual_lover_agent.enterprise.runtime import open_enterprise_runtime
        from virtual_lover_agent.protos import agent_proto_pb2 as proto
        from virtual_lover_agent.protos import agent_proto_pb2_grpc as services
        from virtual_lover_agent.skills.memory.context import RECENT_TURNS
        from virtual_lover_agent.skills.memory.dialogue_memory import MemoryKeys, MemoryService

        requests = queue.Queue()
        answer = "企业模型 API 回复"
        summary = "企业模型记忆摘要"
        model = ENTERPRISE_API["GA_ENTERPRISE_LLM_MODEL"]

        class ModelApiHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.put((self.path, self.headers.get("Authorization"), request))
                metadata = {"id": "chatcmpl-test", "created": 1, "model": request["model"]}
                if request.get("stream"):
                    choices = [
                        {"index": 0, "delta": {"role": "assistant", "content": answer}, "finish_reason": None},
                        {"index": 0, "delta": {}, "finish_reason": "stop"},
                    ]
                    chunks = [
                        {**metadata, "object": "chat.completion.chunk", "choices": [choice]}
                        for choice in choices
                    ]
                    body = ("".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n").encode()
                    content_type = "text/event-stream"
                else:
                    body = json.dumps({
                        **metadata, "object": "chat.completion", "choices": [{
                            "index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": summary},
                        }],
                    }).encode()
                    content_type = "application/json"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        api = self.enterContext(ThreadingHTTPServer(("127.0.0.1", 0), ModelApiHandler))
        worker = threading.Thread(target=api.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        worker.start()
        self.addCleanup(worker.join, 5)
        self.addCleanup(api.shutdown)

        env = {
            **NO_DOTENV,
            **ENTERPRISE_API,
            "GA_INTERNAL_TOKEN": "test-grpc-token",
            "GA_ENTERPRISE_LLM_BASE_URL": f"http://127.0.0.1:{api.server_port}/configured/v1",
            "GA_ENTERPRISE_SUMMARY_BASE_URL": f"http://127.0.0.1:{api.server_port}/summaries/v1",
            "GA_ENTERPRISE_SUMMARY_MODEL": "enterprise-summary",
            "GA_ENTERPRISE_SUMMARY_API_KEY": "test-summary-key",
            "GA_LLM_BASE_URL": "http://127.0.0.1:1/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = EnterpriseSettings.from_env()

        redis = FakeAsyncRedis(decode_responses=True)
        memory = MemoryService(redis)
        for index in range(RECENT_TURNS + 1):
            await memory.save_turn("summary-user", f"question {index}", f"answer {index}")
        summaries = MemoryKeys.for_user("summary-user").summaries
        with patch("redis.asyncio.Redis.from_url", return_value=redis):
            async with open_enterprise_runtime(settings) as runtime:
                server = grpc.aio.server()
                services.add_AgentServiceServicer_to_server(
                    AgentService(runtime.dialogue, settings.internal_token), server,
                )
                grpc_port = server.add_insecure_port("127.0.0.1:0")
                await server.start()
                try:
                    async with grpc.aio.insecure_channel(f"127.0.0.1:{grpc_port}") as channel:
                        stub = services.AgentServiceStub(channel)
                        metadata = (("x-ga-internal-token", settings.internal_token),)
                        prompt = "企业伴侣设定"
                        message = "你好"
                        reply = [item async for item in stub.chatStream(
                            proto.ChatRequest(user_id="enterprise-user", companion_id="companion",
                                              system_prompt=prompt, user_message=message),
                            metadata=metadata, timeout=10,
                        )]
                        self.assertEqual([(item.emotion, item.delta, item.is_end) for item in reply], [
                            ("normal", answer, False), ("done", "", True),
                        ])
                        history = await stub.GetRecentTurns(
                            proto.RecentTurnsRequest(user_id="enterprise-user", companion_id="companion"),
                            metadata=metadata, timeout=5,
                        )
                        self.assertEqual([(item.role, item.content) for item in history.messages], [
                            ("user", message), ("assistant", answer),
                        ])
                        async with asyncio.timeout(8):
                            while not (saved := await redis.lrange(summaries, 0, -1)):
                                await asyncio.sleep(0.02)
                        self.assertEqual(saved, [summary])
                finally:
                    await server.stop(0)

        received = {path: (authorization, body) for path, authorization, body in (
            requests.get_nowait(), requests.get_nowait(),
        )}
        authorization, request = received["/configured/v1/chat/completions"]
        self.assertEqual(authorization, "Bearer test-enterprise-key")
        self.assertEqual(request["model"], model)
        self.assertTrue(request["stream"])
        self.assertEqual(request["messages"], [
            {"role": "system", "content": prompt}, {"role": "user", "content": message},
        ])
        summary_authorization, summary_request = received["/summaries/v1/chat/completions"]
        self.assertEqual(summary_authorization, "Bearer test-summary-key")
        self.assertEqual(summary_request["model"], "enterprise-summary")
