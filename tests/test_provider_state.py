import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app as openclaw


class ProviderStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tmp.name) / "openclaw_config.json"
        self.config_patcher = mock.patch.object(openclaw, "CONFIG_PATH", self.config_path)
        self.config_patcher.start()
        self.env_patcher = mock.patch.dict(os.environ, {"HF_TOKEN": "", "HUGGINGFACE_API_KEY": ""}, clear=False)
        self.env_patcher.start()
        openclaw.HF_TOKEN_CACHE.clear()
        self.client = openclaw.app.test_client()

    def tearDown(self):
        self.env_patcher.stop()
        self.config_patcher.stop()
        self.tmp.cleanup()

    def write_config(self, **overrides):
        config = {**openclaw.DEFAULT_CONFIG, **overrides}
        self.config_path.write_text(json.dumps(config), encoding="utf-8")

    def test_fresh_boot_falls_back_to_local_when_shipped_hf_config_has_no_token(self):
        self.write_config(
            provider="huggingface",
            model="hmellor/tiny-random-LlamaForCausalLM",
            huggingface_api_key="",
        )

        response = self.client.get("/api/settings")

        self.assertEqual(response.status_code, 200)
        settings = response.get_json()["settings"]
        self.assertEqual(settings["provider"], "local")
        self.assertEqual(settings["model"], "openclaw-local")
        self.assertEqual(settings["dormant_huggingface_model"], "hmellor/tiny-random-LlamaForCausalLM")
        self.assertEqual(settings["huggingface_credential_state"], "missing")
        self.assertFalse(settings["huggingface_active"])

    def test_selecting_hf_model_without_token_keeps_model_dormant(self):
        response = self.client.post(
            "/api/huggingface/select",
            json={"model": "openai/gpt-oss-120b", "provider_policy": "cheapest"},
        )

        self.assertEqual(response.status_code, 200)
        settings = response.get_json()["settings"]
        self.assertEqual(settings["provider"], "local")
        self.assertEqual(settings["model"], "openclaw-local")
        self.assertEqual(settings["dormant_huggingface_model"], "openai/gpt-oss-120b")
        self.assertEqual(settings["huggingface_provider_policy"], "cheapest")
        self.assertFalse(settings["huggingface_active"])

    def test_chat_request_for_hf_without_token_uses_local_without_calling_hf(self):
        self.write_config(
            provider="huggingface",
            model="openai/gpt-oss-120b",
            huggingface_api_key="",
        )

        with mock.patch.object(openclaw, "call_huggingface_text", side_effect=AssertionError("HF should stay dormant")):
            response = self.client.post(
                "/api/chat",
                json={
                    "prompt": "Can you help with a task?",
                    "messages": [],
                    "provider": "huggingface",
                    "model": "openai/gpt-oss-120b",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["provider"], "local")
        self.assertEqual(payload["model"], "openclaw-local")
        self.assertNotIn("Provider call failed", payload["reply"])

    def test_hf_quota_failure_marks_token_dormant_and_falls_back_to_local(self):
        token = "hf_test_token"
        self.write_config(
            provider="huggingface",
            model="openai/gpt-oss-120b",
            huggingface_api_key=token,
        )
        openclaw.HF_TOKEN_CACHE[token] = {
            "checked_at": 9999999999,
            "status": {"state": "verified", "active": True, "message": "verified"},
        }

        class QuotaResponse:
            ok = False
            status_code = 402
            reason = "Payment Required"
            text = "credits depleted"

            def json(self):
                return {"error": "credits depleted"}

        with mock.patch.object(openclaw.requests, "post", return_value=QuotaResponse()):
            response = self.client.post(
                "/api/chat",
                json={
                    "prompt": "Use Hugging Face",
                    "messages": [],
                    "provider": "huggingface",
                    "model": "openai/gpt-oss-120b",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["provider"], "local")
        self.assertEqual(payload["model"], "openclaw-local")
        self.assertIn("Hugging Face is dormant", payload["reply"])
        settings = self.client.get("/api/settings").get_json()["settings"]
        self.assertEqual(settings["huggingface_credential_state"], "quota")
        self.assertFalse(settings["huggingface_active"])


if __name__ == "__main__":
    unittest.main()
