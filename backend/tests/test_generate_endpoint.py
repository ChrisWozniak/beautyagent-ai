import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.agent.beauty_agent import process_channel_loop
from backend.app.main import app
from backend.app.models.request_models import GenerateRequest


class GenerateEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
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
                "brief": "Say it repairs your barrier and makes skin eczema-free.",
                "channels": ["instagram"],
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["compliance_status"], "FAILED")
        self.assertEqual(result["detection_source"], "deterministic")
        self.assertIn("repairs your barrier", result["flagged_phrases"])
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
                "brief": "Say it repairs your barrier and makes skin eczema-free.",
                "channels": ["instagram"],
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]

        self.assertNotIn("repairs your barrier", result["final_safe_output"].lower())
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
