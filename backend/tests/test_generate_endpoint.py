import asyncio
from contextlib import redirect_stdout
from io import StringIO
import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.agent.beauty_agent import (
    channel_error_result,
    process_channel_loop,
    process_channel_safely,
)
from backend.app.agent.llm_client import LLMDraftError
from backend.app.agent.strands_agent import build_strands_adapter
from backend.app.config import get_settings
from backend.app.main import app
from backend.app.models.request_models import GenerateRequest, MAX_BRIEF_LENGTH
from backend.app.tools.check_compliance import check_compliance_tool
from backend.scripts.smoke_openrouter import main as openrouter_smoke_main
from backend.scripts.run_red_team_eval import (
    expected_statuses_for_case,
    validate_case,
)


ROOT = Path(__file__).resolve().parents[2]


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

    def test_generate_accepts_omitted_core_actives(self) -> None:
        response = self.client.post(
            "/generate",
            json={
                "brandId": "tower_28",
                "productName": "SOS Daily Rescue Facial Spray",
                "brief": "Announce a calming mist for sensitive-looking skin.",
                "channels": ["instagram"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["error"])

    def test_core_actives_blank_and_null_normalize_to_none(self) -> None:
        base_request = {
            "brandId": "tower_28",
            "productName": "SOS Daily Rescue Facial Spray",
            "brief": "Announce a calming mist.",
            "channels": ["instagram"],
        }

        omitted = GenerateRequest(**base_request)
        blank = GenerateRequest(**{**base_request, "coreActives": "   "})
        null = GenerateRequest(**{**base_request, "coreActives": None})

        self.assertIsNone(omitted.coreActives)
        self.assertIsNone(blank.coreActives)
        self.assertIsNone(null.coreActives)

    def test_brief_character_cap_is_1000(self) -> None:
        GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            brief="x" * MAX_BRIEF_LENGTH,
            channels=["instagram"],
        )

        with self.assertRaises(ValueError):
            GenerateRequest(
                brandId="tower_28",
                productName="SOS Daily Rescue Facial Spray",
                brief="x" * (MAX_BRIEF_LENGTH + 1),
                channels=["instagram"],
            )

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

    def test_expanded_compliance_dictionary_flags_reviewed_phrases(self) -> None:
        result = check_compliance_tool(
            "This antibacterial mist heals acne, repairs your barrier while you sleep, "
            "and the NEA endorses it. Dermatologist prescribed and proven to boost lip fullness."
        )

        self.assertEqual(result["compliance_status"], "FAILED")
        self.assertIn("antibacterial", result["flagged_phrases"])
        self.assertIn("heals acne", result["flagged_phrases"])
        self.assertIn("repairs your barrier while you sleep", result["flagged_phrases"])
        self.assertIn("NEA endorses", result["flagged_phrases"])
        self.assertIn("dermatologist prescribed", result["flagged_phrases"])
        self.assertIn("proven to boost lip fullness", result["flagged_phrases"])
        self.assertIn("refreshing", result["final_safe_output"])
        self.assertIn("helps care for acne-prone skin", result["final_safe_output"])
        self.assertIn("helps support your skin barrier", result["final_safe_output"])
        self.assertIn("follows NEA ingredient guidelines", result["final_safe_output"])
        self.assertIn("gentle on skin", result["final_safe_output"])
        self.assertIn("designed for a fuller-looking shine", result["final_safe_output"])

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

    def test_channel_error_result_uses_contract_error_shape(self) -> None:
        result = channel_error_result("email", "TIMEOUT", "Generation timed out after retries.")

        self.assertEqual(result.channel, "email")
        self.assertEqual(result.generation_status, "error")
        self.assertIsNone(result.raw_draft)
        self.assertIsNone(result.compliance_status)
        self.assertIsNone(result.flagged_phrases)
        self.assertIsNone(result.explanation)
        self.assertIsNone(result.detection_source)
        self.assertIsNone(result.final_safe_output)
        self.assertIsNone(result.retry_exhausted)
        self.assertEqual(result.error.code, "TIMEOUT")

    def test_process_channel_safely_converts_timeout_to_error_result(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Centella",
            brief="Draft one compliant caption.",
            channels=["email"],
        )

        with patch(
            "backend.app.agent.beauty_agent.process_channel_loop",
            side_effect=TimeoutError("too slow"),
        ):
            result = asyncio.run(process_channel_safely(request, "email"))

        self.assertEqual(result.generation_status, "error")
        self.assertEqual(result.error.code, "TIMEOUT")
        self.assertIsNone(result.final_safe_output)

    def test_process_channel_safely_enforces_channel_timeout(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Centella",
            brief="Draft one compliant caption.",
            channels=["email"],
        )

        def slow_channel_loop(_: GenerateRequest, __: str) -> None:
            time.sleep(0.05)

        with (
            patch.dict("os.environ", {"CHANNEL_TIMEOUT_SECONDS": "0.001"}),
            patch(
                "backend.app.agent.beauty_agent.process_channel_loop",
                side_effect=slow_channel_loop,
            ),
        ):
            result = asyncio.run(process_channel_safely(request, "email"))

        self.assertEqual(result.generation_status, "error")
        self.assertEqual(result.error.code, "TIMEOUT")
        self.assertIsNone(result.raw_draft)

    def test_strands_adapter_exposes_compliance_tool(self) -> None:
        adapter = build_strands_adapter()

        self.assertTrue(adapter.tools)
        self.assertIn("check_compliance_tool", adapter.tool_names)
        self.assertEqual(
            adapter.integration_summary(),
            {
                "agent_loop": "process_channel_loop",
                "contract_source": "/generate response models",
                "tools": ["check_compliance_tool"],
                "deterministic_backstop": True,
            },
        )
        tool_result = check_compliance_tool("This makes skin eczema-free.")
        self.assertEqual(tool_result["compliance_status"], "FAILED")

    def test_timeout_settings_have_documented_defaults(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "USE_LLM_DRAFTING": "false",
                "LLM_TIMEOUT_SECONDS": "",
                "LLM_MAX_TOKENS": "",
                "CHANNEL_TIMEOUT_SECONDS": "",
            },
        ):
            settings = get_settings()

        self.assertEqual(settings.llm_timeout_seconds, 15.0)
        self.assertEqual(settings.llm_max_tokens, 1000)
        self.assertEqual(settings.channel_timeout_seconds, 20.0)

    def test_timeout_settings_fallback_on_invalid_values(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "LLM_TIMEOUT_SECONDS": "not-a-number",
                "LLM_MAX_TOKENS": "0",
                "CHANNEL_TIMEOUT_SECONDS": "-1",
            },
        ):
            settings = get_settings()

        self.assertEqual(settings.llm_timeout_seconds, 15.0)
        self.assertEqual(settings.llm_max_tokens, 1000)
        self.assertEqual(settings.channel_timeout_seconds, 20.0)

    def test_openrouter_smoke_test_skips_when_llm_disabled(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "USE_LLM_DRAFTING": "false",
                "OPENROUTER_API_KEY": "test-key",
            },
        ), redirect_stdout(StringIO()):
            exit_code = openrouter_smoke_main()

        self.assertEqual(exit_code, 2)

    def test_red_team_cases_file_has_contract_requests(self) -> None:
        cases_path = ROOT / "backend/evals/red_team_cases.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]

        self.assertGreaterEqual(len(cases), 3)
        for case in cases:
            GenerateRequest(**case["request"])
            validate_case(case)

    def test_red_team_eval_supports_simple_expected_status(self) -> None:
        case = {
            "id": "safe_all_channels",
            "expected_status": "PASSED",
            "request": {
                "brandId": "tower_28",
                "productName": "SOS Daily Rescue Facial Spray",
                "brief": "Draft a gentle caption.",
                "channels": ["tiktok", "instagram"],
            },
        }

        validate_case(case)
        self.assertEqual(
            expected_statuses_for_case(case),
            {"tiktok": "PASSED", "instagram": "PASSED"},
        )

    def test_red_team_eval_supports_per_channel_expected_status(self) -> None:
        case = {
            "id": "mixed_channels",
            "expected_by_channel": {
                "tiktok": "PASSED",
                "instagram": "FAILED",
            },
            "request": {
                "brandId": "tower_28",
                "productName": "SOS Daily Rescue Facial Spray",
                "brief": "Draft copy.",
                "channels": ["tiktok", "instagram"],
            },
        }

        validate_case(case)
        self.assertEqual(
            expected_statuses_for_case(case),
            {"tiktok": "PASSED", "instagram": "FAILED"},
        )

    def test_red_team_eval_rejects_ambiguous_expected_statuses(self) -> None:
        case = {
            "id": "ambiguous",
            "expected_status": "PASSED",
            "expected_by_channel": {"instagram": "PASSED"},
            "request": {
                "brandId": "tower_28",
                "productName": "SOS Daily Rescue Facial Spray",
                "brief": "Draft copy.",
                "channels": ["instagram"],
            },
        }

        with self.assertRaises(ValueError):
            validate_case(case)

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

    def test_health_endpoint_supports_deployment_checks(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
