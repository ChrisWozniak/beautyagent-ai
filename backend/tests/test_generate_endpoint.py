import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


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

