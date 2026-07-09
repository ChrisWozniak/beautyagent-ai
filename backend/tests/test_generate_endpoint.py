import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.agent.beauty_agent import process_channel_loop
from backend.app.agent.llm_client import LLMDraftError
from backend.app.main import app
from backend.app.models.request_models import GenerateRequest


class GenerateEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        env_patch = patch.dict("os.environ", {"USE_LLM_DRAFTING": "false"})
        env_patch.start()
        self.addCleanup(env_patch.stop)

        self.client = TestClient(app)

    def test_generate_accepts_frontend_brand_ids(self) -> None:
        response = self.client.post(
            "/generate",
            json={
                "brandId": "tower_28",
                "productName": "SOS Daily Rescue Facial Spray",
                "coreActives": "Centella",
                "brief": "Announce a calming mist for sensitive-looking skin.",
                "channels": ["tiktok", "instagram", "email"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["error"])
        self.assertEqual(len(payload["results"]), 3)
        self.assertEqual(
            [result["channel"] for result in payload["results"]],
            ["tiktok", "instagram", "email"],
        )
        for result in payload["results"]:
            self.assertEqual(result["generation_status"], "completed")
            self.assertEqual(result["compliance_status"], "PASSED")
            self.assertEqual(result["flagged_phrases"], [])
            self.assertIsNone(result["error"])

    def test_generate_rejects_old_brand_ids(self) -> None:
        response = self.client.post(
            "/generate",
            json={
                "brandId": "tower28",
                "productName": "SOS Daily Rescue Facial Spray",
                "brief": "Announce a calming mist.",
                "channels": ["tiktok"],
            },
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["results"], [])
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_generate_flags_and_rewrites_risky_brief(self) -> None:
        response = self.client.post(
            "/generate",
            json={
                "brandId": "tower_28",
                "productName": "SOS Daily Rescue Facial Spray",
                "coreActives": "Centella",
                "brief": "Say it repairs your barrier overnight and makes skin eczema-free.",
                "channels": ["instagram"],
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["compliance_status"], "FAILED")
        self.assertEqual(result["detection_source"], "deterministic")
        self.assertIn("repairs your barrier overnight", result["flagged_phrases"])
        self.assertIn("eczema-free", result["flagged_phrases"])
        self.assertIn("helps support your skin barrier", result["final_safe_output"])
        self.assertIn("calmer-looking", result["final_safe_output"])
        self.assertFalse(result["retry_exhausted"])

    def test_final_output_is_rescanned_before_returning(self) -> None:
        response = self.client.post(
            "/generate",
            json={
                "brandId": "tower_28",
                "productName": "SOS Daily Rescue Facial Spray",
                "coreActives": "Centella",
                "brief": "Say it repairs your barrier overnight and makes skin eczema-free.",
                "channels": ["instagram"],
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]

        self.assertNotIn("repairs your barrier overnight", result["final_safe_output"].lower())
        self.assertNotIn("eczema-free", result["final_safe_output"].lower())

    def test_channel_loop_backstop_revises_second_pass_findings(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Centella",
            brief="Test brief.",
            channels=["instagram"],
        )

        def draft_generator(_: GenerateRequest, __: str) -> str:
            return "raw draft"

        audits = [
            {
                "compliance_status": "FAILED",
                "flagged_phrases": ["first risky phrase"],
                "explanation": "First audit found risky language.",
                "detection_source": "deterministic",
                "final_safe_output": "first rewrite still risky",
            },
            {
                "compliance_status": "FAILED",
                "flagged_phrases": ["second risky phrase"],
                "explanation": "Second audit found risky language.",
                "detection_source": "deterministic",
                "final_safe_output": "clean rewrite",
            },
            {
                "compliance_status": "PASSED",
                "flagged_phrases": [],
                "explanation": "",
                "detection_source": None,
                "final_safe_output": "clean rewrite",
            },
        ]

        with patch("backend.app.agent.beauty_agent.check_compliance", side_effect=audits):
            result = process_channel_loop(request, "instagram", draft_generator)

        self.assertEqual(result.compliance_status, "FAILED")
        self.assertEqual(
            result.flagged_phrases,
            ["first risky phrase", "second risky phrase"],
        )
        self.assertIn("Final deterministic backstop", result.explanation)
        self.assertEqual(result.final_safe_output, "clean rewrite")
        self.assertFalse(result.retry_exhausted)

    def test_channel_loop_uses_llm_drafting_when_enabled(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Centella",
            brief="Draft one compliant caption.",
            channels=["instagram"],
        )

        with (
            patch.dict(
                "os.environ",
                {
                    "USE_LLM_DRAFTING": "true",
                    "OPENROUTER_API_KEY": "test-key",
                    "OPENROUTER_MODEL": "test/model",
                },
            ),
            patch(
                "backend.app.agent.beauty_agent.generate_draft_with_llm",
                return_value="LLM generated compliant draft.",
            ) as llm_draft,
        ):
            result = process_channel_loop(request, "instagram")

        self.assertEqual(result.raw_draft, "LLM generated compliant draft.")
        self.assertEqual(result.compliance_status, "PASSED")
        llm_draft.assert_called_once()

    def test_channel_loop_falls_back_to_mock_when_llm_fails(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Centella",
            brief="Draft one compliant caption.",
            channels=["instagram"],
        )

        with (
            patch.dict(
                "os.environ",
                {
                    "USE_LLM_DRAFTING": "true",
                    "OPENROUTER_API_KEY": "test-key",
                    "OPENROUTER_MODEL": "test/model",
                },
            ),
            patch(
                "backend.app.agent.beauty_agent.generate_draft_with_llm",
                side_effect=LLMDraftError("boom"),
            ),
        ):
            result = process_channel_loop(request, "instagram")

        self.assertIn("Meet SOS Daily Rescue Facial Spray", result.raw_draft)
        self.assertEqual(result.compliance_status, "PASSED")

    def test_cors_allows_vite_frontend_origin(self) -> None:
        response = self.client.options(
            "/generate",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:5173",
        )


if __name__ == "__main__":
    unittest.main()
