import base64
import io
import json
import os
import wave
from dataclasses import replace
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from virtual_lover_agent.personal.config import PersonalSettings
from virtual_lover_agent.personal.http_server import create_app


def wav_sample() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setparams((1, 2, 16_000, 0, "NONE", "not compressed"))
        audio.writeframes(bytes(3200))
    return output.getvalue()


class PersonalRuntimeTests(TestCase):
    def setUp(self):
        data_dir = self.enterContext(TemporaryDirectory())
        with patch.dict(os.environ, {"PYTHON_DOTENV_DISABLED": "1", "GA_DATA_DIR": data_dir}, clear=True):
            base = PersonalSettings.from_env()
        self.settings = replace(
            base, personal_token="", personal_name="我的伴侣",
            personal_system_prompt="初始人设", personal_voice_id="",
            llm=replace(base.llm, kind="mock"),
            asr=replace(base.asr, kind="mock"), tts=replace(base.tts, kind="mock"),
        )

    def test_standalone_profile_text_voice_and_history_survive_restart(self):
        updated = {"name": "小夏", "system_prompt": "你是小夏。", "voice_id": ""}
        app = create_app(self.settings)
        with TestClient(app) as client:
            token = app.state.runtime.personal_token
            self.assertGreaterEqual(len(token), 40)
            headers = {"Authorization": f"Bearer {token}"}
            self.assertEqual(client.get("/health/ready").json()["mode"], "personal")
            self.assertEqual(client.get("/v1/profile").status_code, 401)
            self.assertEqual(client.get("/v1/profile", headers=headers).json()["name"], "我的伴侣")
            self.assertEqual(client.put("/v1/profile", json=updated, headers=headers).json(), updated)

            stream = client.post("/v1/chat/stream", json={"message": "你好"}, headers=headers)
            events = [json.loads(line[6:]) for line in stream.text.splitlines() if line.startswith("data: ")]
            self.assertEqual(events[-2], {"type": "delta", "delta": "你好"})
            self.assertEqual(events[-1], {"type": "done"})

            audio_headers = {**headers, "Content-Type": "audio/wav"}
            bad = client.post("/v1/voice", content=b"broken", headers=audio_headers)
            self.assertEqual(bad.status_code, 422)
            voice = client.post("/v1/voice", content=wav_sample(), headers=audio_headers)
            self.assertEqual(voice.status_code, 200)
            self.assertTrue(base64.b64decode(voice.json()["audio_base64"]).startswith(b"RIFF"))

        with TestClient(create_app(self.settings)) as restarted:
            self.assertEqual(restarted.app.state.runtime.personal_token, token)
            self.assertEqual(restarted.get("/v1/profile", headers=headers).json(), updated)
            messages = restarted.get("/v1/chat/history", headers=headers).json()["messages"]
            self.assertEqual(len(messages), 4)
            self.assertEqual(messages[0], {"role": "user", "content": "你好"})

    def test_personal_auth_rejects_invalid_credentials_and_preserves_profile(self):
        settings = replace(self.settings, personal_token="test-configured-token")
        with TestClient(create_app(settings)) as client:
            wrong = {"Authorization": "Bearer wrong-token"}
            self.assertEqual(client.get("/v1/chat/history", headers=wrong).status_code, 401)
            self.assertEqual(client.get("/v1/profile", headers=wrong).status_code, 401)
            valid = {"Authorization": "Bearer test-configured-token"}
            response = client.put("/v1/profile", json={"name": "  ", "system_prompt": "x"}, headers=valid)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(client.get("/v1/profile", headers=valid).json()["name"], "我的伴侣")

    def test_summary_defaults_to_single_model_without_cross_endpoint_key_reuse(self):
        env = {
            "PYTHON_DOTENV_DISABLED": "1",
            "GA_DATA_DIR": os.curdir,
            "GA_LLM_PROVIDER": "openai", "GA_LLM_BASE_URL": "http://localhost:8000/v1",
            "GA_LLM_MODEL": "shared-qwen", "GA_LLM_API_KEY": "primary-key",
            "GA_SUMMARY_BASE_URL": "", "GA_SUMMARY_MODEL": "", "GA_SUMMARY_API_KEY": "",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = PersonalSettings.from_env()
            self.assertEqual(settings.summary, settings.llm)
            os.environ["GA_SUMMARY_BASE_URL"] = "http://localhost:8001/v1"
            alternate = PersonalSettings.from_env()
            self.assertEqual(alternate.summary.base_url, "http://localhost:8001/v1")
            self.assertEqual(alternate.summary.api_key, "")
