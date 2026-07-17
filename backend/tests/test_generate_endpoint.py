import asyncio
from contextlib import redirect_stdout
from io import StringIO
import json
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.agent.beauty_agent import (
    channel_error_result,
    draft_channel_copy,
    load_brand_configs,
    product_belongs_to_brand,
    process_channel_loop,
    process_channel_safely,
)
from backend.app.agent.prompts import build_draft_prompt
from backend.app.agent.llm_client import (
    LLMClientError,
    LLMDraftError,
    complete_messages,
    get_llm_usage,
    reset_llm_usage,
    summarize_llm_usage,
)
from backend.app.agent.llm_usage_ledger import summarize_llm_usage_ledger
from backend.app.agent.strands_agent import build_strands_adapter
from backend.app.config import get_settings
from backend.app.config_loader import ConfigLoadError, load_json_config
from backend.app.main import app
from backend.app.models.request_models import GenerateRequest, MAX_BRIEF_LENGTH
from backend.app.models.response_models import GenerateResponse
from backend.app.tools.check_brand_voice import check_brand_voice
from backend.app.tools.check_compliance import check_compliance_tool, load_compliance_rules
from backend.scripts.smoke_generate_live import (
    SMOKE_CASES,
    main as live_generate_smoke_main,
    safe_console_text,
)
from backend.scripts.smoke_openrouter import main as openrouter_smoke_main
from backend.scripts.run_red_team_eval import (
    expected_statuses_for_case,
    run as run_red_team_eval,
    select_cases,
    validate_case,
)
from backend.scripts.run_brand_voice_eval import (
    run as run_brand_voice_eval,
    select_cases as select_brand_voice_cases,
    validate_case as validate_brand_voice_case,
)
from backend.scripts.run_demo_smoke import build_steps as build_demo_smoke_steps


ROOT = Path(__file__).resolve().parents[2]


class GenerateEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        env_patch = patch.dict("os.environ", {"USE_LLM_DRAFTING": "false"})
        env_patch.start()
        self.addCleanup(env_patch.stop)

        self.on_voice_result = {
            "voice_status": "ON_VOICE",
            "voice_confidence": 0.92,
            "voice_reason": "Mocked brand voice result for backend tests.",
        }
        voice_patch = patch(
            "backend.app.agent.beauty_agent.check_brand_voice",
            return_value=self.on_voice_result,
        )
        voice_patch.start()
        self.addCleanup(voice_patch.stop)

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
            self.assertEqual(result["voice_status"], "ON_VOICE")
            self.assertEqual(result["voice_confidence"], 0.92)
            self.assertEqual(result["voice_reason"], "Mocked brand voice result for backend tests.")
            self.assertEqual(result["compliance_status"], "PASSED")
            self.assertEqual(result["compliance_confidence"], 1.0)
            self.assertEqual(result["flagged_phrases"], [])
            self.assertIsNone(result["escalation_trigger"])
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
        self.assertIn("Marketer brief also included risky language", result["explanation"])
        self.assertNotIn("repairs your barrier overnight", result["final_safe_output"].lower())
        self.assertNotIn("eczema-free", result["final_safe_output"].lower())
        self.assertIsNone(result["retry_exhausted"])

    def test_generate_scopes_channel_specific_brief_audit(self) -> None:
        response = self.client.post(
            "/generate",
            json={
                "brandId": "tower_28",
                "productName": "SOS Daily Rescue Facial Spray",
                "coreActives": "Hypochlorous Acid",
                "brief": (
                    "Could we push harder on TikTok and say it clears up eczema flare-ups fast, "
                    "but keep Instagram and email to gentle, soothing language for sensitive skin?"
                ),
                "channels": ["tiktok", "instagram", "email"],
            },
        )

        self.assertEqual(response.status_code, 200)
        results = {result["channel"]: result for result in response.json()["results"]}

        self.assertEqual(results["tiktok"]["compliance_status"], "FAILED")
        self.assertIn("clears up eczema flare-ups", results["tiktok"]["flagged_phrases"])
        self.assertEqual(results["instagram"]["compliance_status"], "PASSED")
        self.assertEqual(results["email"]["compliance_status"], "PASSED")

    def test_expanded_compliance_dictionary_flags_reviewed_phrases(self) -> None:
        result = check_compliance_tool(
            "This antibacterial mist heals acne, repairs your barrier while you sleep, "
            "and the NEA endorses it. Dermatologist prescribed and proven to boost lip fullness. "
            "Reviewers said it cured their eczema and stopped flare-ups for good."
        )

        self.assertEqual(result["compliance_status"], "FAILED")
        self.assertIn("antibacterial", result["flagged_phrases"])
        self.assertIn("heals acne", result["flagged_phrases"])
        self.assertIn("repairs your barrier while you sleep", result["flagged_phrases"])
        self.assertIn("NEA endorses", result["flagged_phrases"])
        self.assertIn("dermatologist prescribed", result["flagged_phrases"])
        self.assertIn("proven to boost lip fullness", result["flagged_phrases"])
        self.assertIn("cured their eczema", result["flagged_phrases"])
        self.assertIn("stopped flare-ups for good", result["flagged_phrases"])
        self.assertIn("refreshing", result["final_safe_output"])
        self.assertIn("helps care for acne-prone skin", result["final_safe_output"])
        self.assertIn("helps support your skin barrier", result["final_safe_output"])
        self.assertIn("follows NEA ingredient guidelines", result["final_safe_output"])
        self.assertIn("gentle on skin", result["final_safe_output"])
        self.assertIn("designed for a fuller-looking shine", result["final_safe_output"])

    def test_compliance_checker_uses_phrase_boundaries_and_negation_context(self) -> None:
        safe_result = check_compliance_tool(
            "Headline it for eczema-prone skin, but include no cure language."
        )

        self.assertEqual(safe_result["compliance_status"], "PASSED")
        self.assertNotIn("cure", safe_result["flagged_phrases"])

        manicure_result = check_compliance_tool("This manicure shade has glossy payoff.")

        self.assertEqual(manicure_result["compliance_status"], "PASSED")
        self.assertNotIn("cure", manicure_result["flagged_phrases"])

    def test_compliance_dictionary_flags_red_team_paraphrases(self) -> None:
        result = check_compliance_tool(
            "It fixes what's broken in your skin's defenses by morning, "
            "stops flare-ups before they start, boosts your skin's collagen production, "
            "reverses fine lines, clears up eczema flare-ups fast, "
            "helps calm and clear up skin irritation, and visibly reduces puffiness and dark circles."
        )

        self.assertEqual(result["compliance_status"], "FAILED")
        self.assertIn("fixes what's broken in your skin's defenses by morning", result["flagged_phrases"])
        self.assertIn("stops flare-ups before they start", result["flagged_phrases"])
        self.assertIn("boosts your skin's collagen production", result["flagged_phrases"])
        self.assertIn("reverses fine lines", result["flagged_phrases"])
        self.assertIn("clears up eczema flare-ups", result["flagged_phrases"])
        self.assertIn("calm and clear up skin irritation", result["flagged_phrases"])
        self.assertIn("visibly reduces puffiness and dark circles", result["flagged_phrases"])

    def test_compliance_explanations_are_deduped_by_rule(self) -> None:
        result = check_compliance_tool(
            "Say it is eczema-free and repairs your barrier overnight."
        )

        self.assertEqual(result["compliance_status"], "FAILED")
        self.assertIn("eczema-free", result["flagged_phrases"])
        self.assertIn("repairs your barrier overnight", result["flagged_phrases"])
        self.assertEqual(
            result["explanation"].count("Cosmetics cannot claim to heal"),
            1,
        )

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
                "compliance_status": "PASSED",
                "flagged_phrases": [],
                "explanation": "",
                "detection_source": None,
                "final_safe_output": "Test brief.",
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
        self.assertIsNone(result.retry_exhausted)

    def test_channel_loop_dedupes_repeated_explanations(self) -> None:
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
                "flagged_phrases": ["draft risky phrase"],
                "explanation": "Shared explanation.",
                "detection_source": "deterministic",
                "final_safe_output": "clean rewrite",
            },
            {
                "compliance_status": "FAILED",
                "flagged_phrases": ["brief risky phrase"],
                "explanation": "Shared explanation.",
                "detection_source": "deterministic",
                "final_safe_output": "Test brief.",
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
            ["draft risky phrase", "brief risky phrase"],
        )
        self.assertEqual(result.explanation.count("Shared explanation."), 1)

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
        self.assertEqual(result.voice_confidence, 0.92)
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

    def test_deterministic_fallback_copy_is_card_friendly_by_channel(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Hypochlorous Acid",
            brief="Draft compliant copy for a launch.",
            channels=["tiktok", "instagram", "email"],
        )

        tiktok = draft_channel_copy(request, "tiktok")
        instagram = draft_channel_copy(request, "instagram")
        email = draft_channel_copy(request, "email")

        self.assertIn("Hook:", tiktok)
        self.assertIn("Script:", tiktok)
        self.assertIn("CTA:", tiktok)
        self.assertIn("Meet SOS Daily Rescue Facial Spray", instagram)
        self.assertNotIn("Brief direction:", instagram)
        self.assertTrue(email.startswith("Subject:"))
        self.assertIn("\n\nBody:", email)

    def test_half_magic_fallback_uses_matching_brand_and_product_claim(self) -> None:
        request = GenerateRequest(
            brandId="half_magic",
            productName="Magic Drip Glitter Lipgloss",
            coreActives="Vitamin E, Jojoba Oil",
            brief="Draft a fun email about glitter payoff and shine.",
            channels=["email"],
        )

        email = draft_channel_copy(request, "email")
        tiktok = draft_channel_copy(request, "tiktok")

        self.assertIn("from Half Magic", tiktok)
        self.assertNotIn("Tower 28", tiktok)
        self.assertNotIn("Tower 28", email)
        self.assertIn("delivers high-shine glitter payoff", email)
        self.assertIn("quick shine reset", tiktok)
        self.assertIn("Swipe it on", tiktok)
        self.assertNotIn("Spritz", tiktok)
        self.assertNotIn("keeps the message", email)
        self.assertNotIn("compliant", email.lower())

    def test_tower_28_spray_fallback_does_not_use_lip_or_makeup_actions(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Hypochlorous Acid",
            brief="Draft a quick TikTok for a calming skin spray.",
            channels=["tiktok"],
        )

        tiktok = draft_channel_copy(request, "tiktok")

        self.assertIn("Spritz it", tiktok)
        self.assertNotIn("Swipe it on", tiktok)
        self.assertNotIn("Line it up", tiktok)
        self.assertNotIn("Paint it on", tiktok)
        self.assertNotIn("Press it on", tiktok)

    def test_generate_accepts_free_text_product_name(self) -> None:
        response = self.client.post(
            "/generate",
            json={
                "brandId": "tower_28",
                "productName": "SOS spray",
                "brief": "Draft a product launch post.",
                "channels": ["tiktok"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["results"][0]["generation_status"], "completed")
        self.assertIn("SOS spray", payload["results"][0]["raw_draft"])

    def test_generate_returns_internal_error_for_unexpected_top_level_failure(self) -> None:
        with patch(
            "backend.app.main.generate_mock_response",
            side_effect=RuntimeError("boom"),
        ):
            response = self.client.post(
                "/generate",
                json={
                    "brandId": "tower_28",
                    "productName": "SOS Daily Rescue Facial Spray",
                    "brief": "Draft a gentle caption.",
                    "channels": ["instagram"],
                },
            )

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["results"], [])
        self.assertEqual(payload["error"]["code"], "INTERNAL_ERROR")
        self.assertEqual(payload["error"]["message"], "Internal server error.")
        self.assertIsNone(payload["error"]["detail"])

    def test_generate_returns_internal_error_for_config_load_failure(self) -> None:
        with patch(
            "backend.app.main.generate_mock_response",
            side_effect=ConfigLoadError("brand config file contains invalid JSON"),
        ):
            response = self.client.post(
                "/generate",
                json={
                    "brandId": "tower_28",
                    "productName": "SOS Daily Rescue Facial Spray",
                    "brief": "Draft a gentle caption.",
                    "channels": ["instagram"],
                },
            )

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "INTERNAL_ERROR")
        self.assertIn("invalid JSON", payload["error"]["detail"])

    def test_channel_error_result_uses_contract_error_shape(self) -> None:
        result = channel_error_result("email", "TIMEOUT", "Generation timed out after retries.")

        self.assertEqual(result.channel, "email")
        self.assertEqual(result.generation_status, "error")
        self.assertIsNone(result.raw_draft)
        self.assertIsNone(result.voice_status)
        self.assertIsNone(result.voice_confidence)
        self.assertIsNone(result.voice_reason)
        self.assertIsNone(result.compliance_status)
        self.assertIsNone(result.compliance_confidence)
        self.assertIsNone(result.flagged_phrases)
        self.assertIsNone(result.explanation)
        self.assertIsNone(result.detection_source)
        self.assertIsNone(result.final_safe_output)
        self.assertIsNone(result.retry_exhausted)
        self.assertIsNone(result.escalation_trigger)
        self.assertEqual(result.error.code, "TIMEOUT")

    def test_week2_needs_human_review_contract_shape_is_supported(self) -> None:
        payload = {
            "results": [
                {
                    "channel": "instagram",
                    "generation_status": "completed",
                    "raw_draft": "POV your skin said no today.",
                    "voice_status": "DRIFTED",
                    "voice_confidence": 0.42,
                    "voice_reason": "Uses meme-speak structure that does not match the brand voice profile.",
                    "compliance_status": "NEEDS_HUMAN_REVIEW",
                    "compliance_confidence": None,
                    "flagged_phrases": None,
                    "explanation": None,
                    "detection_source": None,
                    "final_safe_output": None,
                    "retry_exhausted": None,
                    "escalation_trigger": "voice",
                    "error": None,
                }
            ],
            "error": None,
        }

        response = GenerateResponse(**payload)

        self.assertEqual(response.results[0].compliance_status, "NEEDS_HUMAN_REVIEW")
        self.assertEqual(response.results[0].escalation_trigger, "voice")

    def test_channel_loop_routes_voice_drift_after_clean_deterministic_precheck(self) -> None:
        request = GenerateRequest(
            brandId="half_magic",
            productName="Magic Drip Glitter Lipgloss",
            coreActives="Vitamin E, Jojoba Oil",
            brief="Draft one safe caption.",
            channels=["instagram"],
        )

        def draft_generator(_: GenerateRequest, __: str) -> str:
            return "Paint it bold and tag us in the gloss chaos."

        def drifted_voice_checker(*_args: object) -> dict[str, object]:
            return {
                "voice_status": "DRIFTED",
                "voice_confidence": 0.34,
                "voice_reason": "The copy misses Half Magic's backstage-friend voice.",
            }

        result = process_channel_loop(
            request,
            "instagram",
            draft_generator,
            drifted_voice_checker,
        )

        self.assertEqual(result.generation_status, "completed")
        self.assertEqual(result.raw_draft, "Paint it bold and tag us in the gloss chaos.")
        self.assertEqual(result.voice_status, "DRIFTED")
        self.assertEqual(result.voice_confidence, 0.34)
        self.assertEqual(result.compliance_status, "NEEDS_HUMAN_REVIEW")
        self.assertIsNone(result.compliance_confidence)
        self.assertIsNone(result.flagged_phrases)
        self.assertIsNone(result.explanation)
        self.assertIsNone(result.detection_source)
        self.assertIsNone(result.final_safe_output)
        self.assertIsNone(result.retry_exhausted)
        self.assertEqual(result.escalation_trigger, "voice")

    def test_channel_loop_surfaces_brief_compliance_even_when_voice_drifted(self) -> None:
        request = GenerateRequest(
            brandId="half_magic",
            productName="Go Plump Yourself Extreme Plumping Lip Liner",
            coreActives="",
            brief="Say it's clinically proven to increase lip volume.",
            channels=["tiktok"],
        )

        def draft_generator(_: GenerateRequest, __: str) -> str:
            return (
                "Hook: A fuller-looking lip effect, minus the overthinking.\n"
                "Script: Swipe, shine, go.\n"
                "CTA: Shop now."
            )

        def drifted_voice_checker(*_args: object) -> dict[str, object]:
            return {
                "voice_status": "DRIFTED",
                "voice_confidence": 0.78,
                "voice_reason": "The copy is close but too generic for Half Magic.",
            }

        result = process_channel_loop(
            request,
            "tiktok",
            draft_generator,
            drifted_voice_checker,
        )

        self.assertEqual(result.generation_status, "completed")
        self.assertEqual(result.voice_status, "DRIFTED")
        self.assertEqual(result.compliance_status, "FAILED")
        self.assertEqual(result.compliance_confidence, 1.0)
        self.assertEqual(result.flagged_phrases, ["clinically proven"])
        self.assertIn("Marketer brief also included risky language", result.explanation)
        self.assertEqual(result.detection_source, "deterministic")
        self.assertEqual(result.escalation_trigger, "compliance")

    def test_channel_loop_skips_compliance_when_voice_confidence_is_low(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Hypochlorous Acid",
            brief="Draft one caption.",
            channels=["tiktok"],
        )

        def draft_generator(_: GenerateRequest, __: str) -> str:
            return "Mist, glow, done."

        def low_confidence_voice_checker(*_args: object) -> dict[str, object]:
            return {
                "voice_status": "ON_VOICE",
                "voice_confidence": 0.7,
                "voice_reason": "The copy is close but too generic to confirm Tower 28 channel fit.",
            }

        passed_audit = {
            "compliance_status": "PASSED",
            "compliance_confidence": 1.0,
            "flagged_phrases": [],
            "explanation": "",
            "detection_source": None,
            "final_safe_output": "Mist, glow, done.",
        }

        with patch(
            "backend.app.agent.beauty_agent.check_compliance",
            return_value=passed_audit,
        ) as compliance:
            result = process_channel_loop(
                request,
                "tiktok",
                draft_generator,
                low_confidence_voice_checker,
            )

        self.assertEqual(result.voice_status, "ON_VOICE")
        self.assertEqual(result.voice_confidence, 0.7)
        self.assertEqual(result.compliance_status, "NEEDS_HUMAN_REVIEW")
        self.assertEqual(result.escalation_trigger, "voice")
        self.assertIsNone(result.final_safe_output)
        self.assertEqual(compliance.call_count, 2)

    def test_channel_loop_runs_compliance_when_voice_passes_threshold(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Hypochlorous Acid",
            brief="Draft one caption.",
            channels=["email"],
        )

        def draft_generator(_: GenerateRequest, __: str) -> str:
            return "A gentle daily refresh for sensitive-looking skin."

        result = process_channel_loop(request, "email", draft_generator)

        self.assertEqual(result.voice_status, "ON_VOICE")
        self.assertEqual(result.voice_confidence, 0.92)
        self.assertEqual(result.compliance_status, "PASSED")
        self.assertEqual(result.compliance_confidence, 1.0)
        self.assertIsNone(result.escalation_trigger)
        self.assertEqual(result.final_safe_output, result.raw_draft)
        self.assertIsNone(result.retry_exhausted)

    def test_channel_loop_routes_low_confidence_compliance_to_human_review(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Hypochlorous Acid",
            brief="Draft one caption.",
            channels=["instagram"],
        )

        def draft_generator(_: GenerateRequest, __: str) -> str:
            return "A gentle daily refresh for sensitive-looking skin."

        audits = [
            {
                "compliance_status": "FAILED",
                "compliance_confidence": 0.61,
                "flagged_phrases": ["borderline claim"],
                "explanation": "LLM audit was not confident enough to approve the rewrite.",
                "detection_source": "llm_audit",
                "final_safe_output": "A safer rewrite.",
            },
            {
                "compliance_status": "PASSED",
                "compliance_confidence": 1.0,
                "flagged_phrases": [],
                "explanation": "",
                "detection_source": None,
                "final_safe_output": "Draft one caption.",
            },
        ]

        with patch("backend.app.agent.beauty_agent.check_compliance", side_effect=audits):
            result = process_channel_loop(request, "instagram", draft_generator)

        self.assertEqual(result.voice_status, "ON_VOICE")
        self.assertEqual(result.compliance_status, "NEEDS_HUMAN_REVIEW")
        self.assertEqual(result.compliance_confidence, 0.61)
        self.assertEqual(result.flagged_phrases, ["borderline claim"])
        self.assertEqual(result.detection_source, "llm_audit")
        self.assertIsNone(result.final_safe_output)
        self.assertIsNone(result.retry_exhausted)
        self.assertEqual(result.escalation_trigger, "compliance")

    def test_brand_configs_include_week2_voice_profiles(self) -> None:
        brands = load_brand_configs()

        tower_voice = brands["tower_28"]["voice"]
        half_magic_voice = brands["half_magic"]["voice"]

        self.assertIn("Good Clean Fun", tower_voice)
        self.assertIn("expert-not-clinical", tower_voice)
        self.assertIn("TikTok", tower_voice)
        self.assertIn("eczema-prone skin", tower_voice)
        self.assertIn("backstage-friend voice", half_magic_voice)
        self.assertIn("experimentation & artistry", half_magic_voice)
        self.assertIn("Donni Davy", half_magic_voice)
        self.assertIn("TikTok", half_magic_voice)

    def test_brand_configs_use_exact_runtime_voice_files(self) -> None:
        tower_path = ROOT / "backend/app/data/brand_voice_tower28.md"
        half_magic_path = ROOT / "backend/app/data/brand_voice_halfmagic.md"
        expected_tower_voice = (
            '[TOWER 28 (tower_28_beauty): Makeup for sensitive/reactive/eczema-prone skin. '
            'Mission: "Good Clean Fun"; ethos: "It\'s ok to be sensitive." Voice: '
            'approachable, friendly, conversational, expert-not-clinical; 8.5/10 casual. '
            'Tagline: "Sensitive skin deserves fun makeup." Avoid: "medically proven," '
            '"toxin-free," "anti-aging miracle," unverified derm-recommended claims. NEVER '
            'claim to cure/heal/treat eczema, rosacea, or acne — speak to comfort & support '
            'instead. Compliance: frame as "safe for" eczema-prone skin; "hypoallergenic" '
            'only w/ HRIPT-test reference; SOS Spray — use soothes/purifies/calms, never '
            'sanitizer/disinfectant; NEA claims: "follows NEA Seal of Acceptance," never '
            '"NEA-endorsed." IG: 75-250 words, 1-3 emoji (✨💖☀️👀🤍🌊), CTA "find your '
            'shade"/"shop now". TikTok: hook-demo-result-CTA, friend/creator voice, <150 '
            'chars, CTAs low-pressure. Email: benefit-driven subject, 30-50 chars, 0-1 emoji. '
            'Visual: real skin texture, sunny daylight, no clinical/lab imagery.]'
        )
        expected_half_magic_voice = (
            '[HALF MAGIC (half_magic_beauty): Editorial makeup brand founded by Donni Davy '
            '(Euphoria). Sells experimentation & artistry, not correction/perfection. Voice: '
            'bold, artistic, playful, confident, expressive, inclusive, irreverent; 9/10 '
            'casual. Avoid: flawless, perfect skin, anti-aging, corrective, hide '
            'imperfections, beauty rules, clinical tone, medical claims. Compliance: '
            'glitter/pigment/liner near eyes -> include eye-safety usage note (verify per '
            'SKU); Face Gems -> always note medical-grade, irritation-free adhesive, no lash '
            'glue needed. IG: 100-250 words, hook first, moderate emoji (✨💜🖤🌈💫⚡🪩👁️), '
            'CTA like “tag us”/“shop now”. TikTok: fast, tutorial/trend style, '
            'backstage-friend voice, <100-char caption. Email: playful/curious subject, '
            '25-45 chars, casual. Visual: electric purple, chrome, cobalt, hot pink, lime, '
            'holographic; maximalist editorial, real skin texture, no “clean girl” '
            'minimalism.]'
        )

        tower_file_voice = tower_path.read_text(encoding="utf-8").rstrip("\n")
        half_magic_file_voice = half_magic_path.read_text(encoding="utf-8").rstrip("\n")
        brands = load_brand_configs()

        self.assertEqual(tower_file_voice, expected_tower_voice)
        self.assertEqual(half_magic_file_voice, expected_half_magic_voice)
        self.assertEqual(brands["tower_28"]["voice"], expected_tower_voice)
        self.assertEqual(brands["half_magic"]["voice"], expected_half_magic_voice)

    def test_check_brand_voice_parses_on_voice_result(self) -> None:
        brand_config = load_brand_configs()["tower_28"]
        raw_voice_result = json.dumps(
            {
                "voice_status": "ON_VOICE",
                "voice_confidence": 0.91,
                "voice_reason": "The phrase 'It's OK to be sensitive' matches the approachable Tower 28 voice.",
            }
        )

        with patch(
            "backend.app.tools.check_brand_voice.complete_messages",
            return_value=raw_voice_result,
        ) as complete:
            result = check_brand_voice(
                "It's OK to be sensitive - mist, glow, keep going.",
                "tower_28",
                brand_config,
                "instagram",
            )

        self.assertEqual(result["voice_status"], "ON_VOICE")
        self.assertEqual(result["voice_confidence"], 0.91)
        self.assertIn("approachable Tower 28 voice", result["voice_reason"])
        complete.assert_called_once()
        self.assertEqual(complete.call_args.args[2], get_settings().anthropic_model_sonnet)

    def test_check_brand_voice_extracts_json_from_wrapped_response(self) -> None:
        brand_config = load_brand_configs()["half_magic"]
        wrapped_response = """
        Here is the evaluation:
        {"voice_status": "DRIFTED", "voice_confidence": 0.32, "voice_reason": "The clinical phrase 'reduces visible aging' misses the playful backstage-friend voice."}
        """

        with patch(
            "backend.app.tools.check_brand_voice.complete_messages",
            return_value=wrapped_response,
        ):
            result = check_brand_voice(
                "Reduces visible aging with a clinically precise finish.",
                "half_magic",
                brand_config,
                "tiktok",
            )

        self.assertEqual(result["voice_status"], "DRIFTED")
        self.assertEqual(result["voice_confidence"], 0.32)
        self.assertIn("backstage-friend voice", result["voice_reason"])

    def test_check_brand_voice_fails_closed_on_malformed_response(self) -> None:
        brand_config = load_brand_configs()["tower_28"]

        with patch(
            "backend.app.tools.check_brand_voice.complete_messages",
            return_value="not json",
        ):
            result = check_brand_voice(
                "Generic caption.",
                "tower_28",
                brand_config,
                "email",
            )

        self.assertEqual(result["voice_status"], "DRIFTED")
        self.assertEqual(result["voice_confidence"], 0.0)
        self.assertIn("needs human review", result["voice_reason"])

    def test_check_brand_voice_recovers_plain_text_drifted_verdict(self) -> None:
        brand_config = load_brand_configs()["tower_28"]

        with patch(
            "backend.app.tools.check_brand_voice.complete_messages",
            return_value="DRIFTED",
        ):
            result = check_brand_voice(
                "Subject: Protocol-grade skin maintenance",
                "tower_28",
                brand_config,
                "email",
            )

        self.assertEqual(result["voice_status"], "DRIFTED")
        self.assertEqual(result["voice_confidence"], 0.0)
        self.assertIn("without structured JSON", result["voice_reason"])

    def test_check_brand_voice_recovers_plain_text_on_voice_verdict(self) -> None:
        brand_config = load_brand_configs()["half_magic"]

        with patch(
            "backend.app.tools.check_brand_voice.complete_messages",
            return_value="ON_VOICE - Uses ALL CAPS product naming and playful creator cadence.",
        ):
            result = check_brand_voice(
                "MAGIC DRIP said sparkle now, overthink never.",
                "half_magic",
                brand_config,
                "tiktok",
            )

        self.assertEqual(result["voice_status"], "ON_VOICE")
        self.assertEqual(result["voice_confidence"], 1.0)
        self.assertIn("ALL CAPS", result["voice_reason"])

    def test_check_brand_voice_fails_closed_on_llm_error(self) -> None:
        brand_config = load_brand_configs()["half_magic"]

        with patch(
            "backend.app.tools.check_brand_voice.complete_messages",
            side_effect=LLMClientError("network down"),
        ):
            result = check_brand_voice(
                "Paint it loud.",
                "half_magic",
                brand_config,
                "instagram",
            )

        self.assertEqual(result["voice_status"], "DRIFTED")
        self.assertEqual(result["voice_confidence"], 0.0)
        self.assertIn("needs human review", result["voice_reason"])

    def test_complete_messages_logs_provider_error_without_secret(self) -> None:
        settings = SimpleNamespace(
            anthropic_api_key="test-secret-key",
            openrouter_api_key=None,
            openrouter_model="openrouter/test-model",
            llm_max_tokens=500,
            llm_timeout_seconds=15,
        )

        def failing_completion(**_kwargs: object) -> object:
            raise RuntimeError("provider rejected model id")

        fake_litellm = SimpleNamespace(completion=failing_completion)
        output = StringIO()

        with patch.dict(sys.modules, {"litellm": fake_litellm}):
            with redirect_stdout(output):
                with self.assertRaises(LLMClientError):
                    complete_messages(
                        [{"role": "user", "content": "hello"}],
                        settings,
                        "anthropic/test-sonnet",
                        temperature=0.1,
                        call_name="brand_voice",
                    )

        log_line = output.getvalue()
        self.assertIn("[llm-error]", log_line)
        self.assertIn("call_name=brand_voice", log_line)
        self.assertIn("model=anthropic/test-sonnet", log_line)
        self.assertIn("error_type=RuntimeError", log_line)
        self.assertIn("provider rejected model id", log_line)
        self.assertNotIn("test-secret-key", log_line)

    def test_build_draft_prompt_includes_brand_compliance_notes(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Hypochlorous Acid",
            brief="Draft one caption.",
            channels=["instagram"],
        )

        messages = build_draft_prompt(
            request,
            "instagram",
            load_brand_configs()["tower_28"],
            "refreshes skin throughout the day",
        )

        user_prompt = messages[1]["content"]
        self.assertIn("Brand compliance notes:", user_prompt)
        self.assertIn("Avoid disease-treatment language.", user_prompt)
        self.assertIn("Do not imply the product changes skin structure", user_prompt)
        self.assertIn("Product detail: Hypochlorous Acid", user_prompt)
        self.assertIn(
            "Use the product name exactly as written: SOS Daily Rescue Facial Spray",
            user_prompt,
        )
        self.assertIn("Return only the requested channel's draft copy", messages[0]["content"])
        self.assertIn("Do not include compliance reasoning", user_prompt)
        self.assertIn("Do not include labels for other channels", user_prompt)
        self.assertIn("Preserve the product name spelling exactly", user_prompt)

    def test_build_draft_prompt_includes_exact_runtime_voice_profile(self) -> None:
        request = GenerateRequest(
            brandId="half_magic",
            productName="Magic Drip Glitter Lipgloss",
            coreActives="Vitamin E, Jojoba Oil",
            brief="Draft one TikTok script.",
            channels=["tiktok"],
        )
        brand_config = load_brand_configs()["half_magic"]

        messages = build_draft_prompt(
            request,
            "tiktok",
            brand_config,
            "delivers high-shine glitter payoff",
        )

        user_prompt = messages[1]["content"]
        self.assertIn(f"Brand voice: {brand_config['voice']}", user_prompt)
        self.assertIn("Editorial makeup brand founded by Donni Davy", user_prompt)
        self.assertIn("backstage-friend voice", user_prompt)

    def test_build_draft_prompt_uses_week2_channel_specs(self) -> None:
        request = GenerateRequest(
            brandId="tower_28",
            productName="SOS Daily Rescue Facial Spray",
            coreActives="Hypochlorous Acid",
            brief="Draft one caption.",
            channels=["instagram"],
        )

        instagram_prompt = build_draft_prompt(
            request,
            "instagram",
            load_brand_configs()["tower_28"],
            "refreshes skin throughout the day",
        )[1]["content"]
        self.assertIn("zero hashtags", instagram_prompt)
        self.assertIn("No hashtag blocks", instagram_prompt)
        self.assertNotIn("optional light hashtags", instagram_prompt)

        email_prompt = build_draft_prompt(
            request,
            "email",
            load_brand_configs()["tower_28"],
            "refreshes skin throughout the day",
        )[1]["content"]
        self.assertIn("Body should be 3-5 sentences max", email_prompt)
        self.assertIn("Subject: [subject line, 30-50 chars]", email_prompt)

        tiktok_prompt = build_draft_prompt(
            request,
            "tiktok",
            load_brand_configs()["tower_28"],
            "refreshes skin throughout the day",
        )[1]["content"]
        self.assertIn("hook, demo/script, and a soft low-pressure CTA", tiktok_prompt)
        self.assertIn("<150 chars per section", tiktok_prompt)
        self.assertIn("No hashtags in the script body", tiktok_prompt)

    def test_build_draft_prompt_prevents_channel_bleed_for_multi_channel_brief(self) -> None:
        request = GenerateRequest(
            brandId="half_magic",
            productName="Magic Drip Glitter Lipgloss",
            coreActives="Vitamin E, Jojoba Oil",
            brief="Write an email and Instagram caption with a bold CTA.",
            channels=["email", "instagram"],
        )

        instagram_prompt = build_draft_prompt(
            request,
            "instagram",
            load_brand_configs()["half_magic"],
            "delivers high-shine glitter payoff",
        )[1]["content"]

        self.assertIn("Channel: instagram", instagram_prompt)
        self.assertIn("Write copy for this channel only", instagram_prompt)
        self.assertIn("EMAIL SUBJECT LINE", instagram_prompt)
        self.assertIn("INSTAGRAM CAPTION", instagram_prompt)
        self.assertIn("Do not include compliance reasoning", instagram_prompt)
        self.assertIn("Do not include compliance reasoning, refusals, explanations, notes, or markdown dividers", instagram_prompt)

    def test_compliance_rules_do_not_flag_plump_product_name_words(self) -> None:
        phrases = {rule["phrase"] for rule in load_compliance_rules()}

        self.assertNotIn("plump", phrases)
        self.assertNotIn("plumper", phrases)
        self.assertNotIn("plumping", phrases)
        self.assertIn("proven to boost lip fullness", phrases)

    def test_check_brand_voice_prompt_uses_exact_runtime_voice_profile(self) -> None:
        brand_config = load_brand_configs()["tower_28"]

        with patch(
            "backend.app.tools.check_brand_voice.complete_messages",
            return_value=json.dumps(
                {
                    "voice_status": "ON_VOICE",
                    "voice_confidence": 0.91,
                    "voice_reason": "The phrase 'It's OK to be sensitive' matches the Tower 28 voice.",
                }
            ),
        ) as complete:
            check_brand_voice(
                "It's OK to be sensitive - shop now.",
                "tower_28",
                brand_config,
                "instagram",
            )

        messages = complete.call_args.args[0]
        user_prompt = messages[1]["content"]
        self.assertIn(f"Brand voice profile:\n{brand_config['voice']}", user_prompt)
        self.assertIn("Good Clean Fun", user_prompt)
        self.assertIn("Sensitive skin deserves fun makeup", user_prompt)

    def test_build_draft_prompt_omits_blank_product_detail(self) -> None:
        request = GenerateRequest(
            brandId="half_magic",
            productName="Celestial Liner",
            coreActives=" ",
            brief="Draft one caption for a makeup launch.",
            channels=["instagram"],
        )

        messages = build_draft_prompt(
            request,
            "instagram",
            load_brand_configs()["half_magic"],
            "creates expressive eye looks",
        )

        user_prompt = messages[1]["content"]
        self.assertIn("Product: Celestial Liner", user_prompt)
        self.assertNotIn("Core actives:", user_prompt)
        self.assertNotIn("Product detail:", user_prompt)
        self.assertNotIn("not provided", user_prompt)

    def test_load_json_config_fails_loudly_on_invalid_json(self) -> None:
        with TemporaryDirectory() as temp_dir:
            bad_config = Path(temp_dir) / "bad.json"
            bad_config.write_text('{"broken": ', encoding="utf-8")

            with self.assertRaises(ConfigLoadError) as error:
                load_json_config(bad_config, "test")

        self.assertIn("test config file contains invalid JSON", str(error.exception))

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

    def test_live_generate_smoke_test_skips_when_llm_disabled(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "USE_LLM_DRAFTING": "false",
                "OPENROUTER_API_KEY": "test-key",
            },
        ), redirect_stdout(StringIO()):
            exit_code = live_generate_smoke_main()

        self.assertEqual(exit_code, 2)

    def test_live_generate_smoke_cases_cover_both_week2_brands(self) -> None:
        self.assertEqual(
            {case.brandId for case in SMOKE_CASES},
            {"tower_28", "half_magic"},
        )
        self.assertEqual(len(SMOKE_CASES), 2)

    def test_safe_console_text_escapes_emoji_for_windows_output(self) -> None:
        preview = safe_console_text("gloss ✨ shine\nnow", limit=20)

        self.assertEqual(preview, "gloss \\u2728 shine now")

    def test_llm_usage_summary_records_litellm_usage_metadata(self) -> None:
        from backend.app.agent import llm_client

        reset_llm_usage()
        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "usage.jsonl"
            response = SimpleNamespace(
                usage=SimpleNamespace(
                    prompt_tokens=120,
                    completion_tokens=35,
                    total_tokens=155,
                ),
                _hidden_params={"response_cost": 0.0042},
            )

            with patch.dict("os.environ", {"LLM_USAGE_LEDGER_PATH": str(ledger_path)}):
                llm_client._record_usage(response, "anthropic/test-model", "generation")

            records = get_llm_usage()
            summary = summarize_llm_usage()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].call_name, "generation")
            self.assertEqual(records[0].model, "anthropic/test-model")
            self.assertEqual(records[0].prompt_tokens, 120)
            self.assertEqual(records[0].completion_tokens, 35)
            self.assertEqual(records[0].total_tokens, 155)
            self.assertEqual(records[0].cost_usd, 0.0042)
            self.assertEqual(
                summary,
                {
                    "calls": 1,
                    "prompt_tokens": 120,
                    "completion_tokens": 35,
                    "total_tokens": 155,
                    "cost_usd": 0.0042,
                },
            )
            ledger_lines = ledger_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(ledger_lines), 1)
            ledger_entry = json.loads(ledger_lines[0])
            self.assertEqual(ledger_entry["call_name"], "generation")
            self.assertEqual(ledger_entry["model"], "anthropic/test-model")
            self.assertEqual(ledger_entry["total_tokens"], 155)
            self.assertEqual(ledger_entry["cost_usd"], 0.0042)
            self.assertIn("timestamp_utc", ledger_entry)
            self.assertNotIn("prompt", ledger_entry)
            self.assertNotIn("response", ledger_entry)

    def test_llm_usage_ledger_summarizes_grand_total(self) -> None:
        from backend.app.agent import llm_client

        reset_llm_usage()
        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "usage.jsonl"
            first_response = SimpleNamespace(
                usage=SimpleNamespace(
                    prompt_tokens=100,
                    completion_tokens=25,
                    total_tokens=125,
                ),
                _hidden_params={"response_cost": 0.001},
            )
            second_response = SimpleNamespace(
                usage=SimpleNamespace(
                    prompt_tokens=200,
                    completion_tokens=50,
                    total_tokens=250,
                ),
                _hidden_params={"response_cost": 0.0025},
            )

            with patch.dict("os.environ", {"LLM_USAGE_LEDGER_PATH": str(ledger_path)}):
                llm_client._record_usage(first_response, "anthropic/model-a", "generation")
                llm_client._record_usage(second_response, "anthropic/model-a", "brand_voice")
                with ledger_path.open("a", encoding="utf-8") as ledger_file:
                    ledger_file.write("not-json\n")

                self.assertEqual(
                    summarize_llm_usage_ledger(),
                    {
                        "calls": 2,
                        "prompt_tokens": 300,
                        "completion_tokens": 75,
                        "total_tokens": 375,
                        "cost_usd": 0.0035,
                    },
                )

    def test_llm_usage_summary_handles_missing_usage_metadata(self) -> None:
        reset_llm_usage()

        self.assertEqual(
            summarize_llm_usage(),
            {
                "calls": 0,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "cost_usd": None,
            },
        )

    def test_red_team_cases_file_has_contract_requests(self) -> None:
        cases_path = ROOT / "backend/evals/red_team_cases.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]

        self.assertEqual(len(cases), 20)
        for case in cases:
            GenerateRequest(**case["request"])
            validate_case(case)

    def test_red_team_cases_use_configured_products(self) -> None:
        cases_path = ROOT / "backend/evals/red_team_cases.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]

        for case in cases:
            request = case["request"]
            with self.subTest(case=case["id"]):
                self.assertTrue(
                    product_belongs_to_brand(
                        request["brandId"],
                        request["productName"],
                    )
                )

    def test_brand_voice_calibration_cases_file_has_expected_shape(self) -> None:
        cases_path = ROOT / "backend/evals/brand_voice_calibration_cases.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]

        self.assertEqual(len(cases), 6)
        self.assertEqual(
            {case["brandId"] for case in cases},
            {"tower_28", "half_magic"},
        )
        self.assertEqual(
            {case["expected_voice_status"] for case in cases},
            {"ON_VOICE", "DRIFTED"},
        )
        for case in cases:
            validate_brand_voice_case(case)
            self.assertIn(case["channel"], {"tiktok", "instagram", "email"})

    def test_live_ui_sample_payloads_match_response_contract(self) -> None:
        samples_dir = ROOT / "shared/live-ui-samples"
        sample_paths = [ROOT / "sample_response.json"]
        sample_paths.extend(sorted(samples_dir.glob("*.response.json")))

        self.assertGreaterEqual(len(sample_paths), 5)
        for sample_path in sample_paths:
            with self.subTest(sample=sample_path.name):
                payload = json.loads(sample_path.read_text(encoding="utf-8"))
                GenerateResponse(**payload)
                for result in payload["results"]:
                    self.assertIn("error", result)

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

    def test_red_team_eval_run_can_mock_brand_voice_gate(self) -> None:
        with redirect_stdout(StringIO()) as output:
            exit_code = run_red_team_eval(
                [
                    "--case-id",
                    "risky_barrier_claim",
                    "--mock-brand-voice",
                    "--compact",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("1/1 selected cases passed", output.getvalue())

    def test_demo_smoke_steps_match_pre_demo_checks(self) -> None:
        steps = build_demo_smoke_steps()

        self.assertEqual(
            [step.name for step in steps],
            [
                "Backend unit tests",
                "Token-safe red-team compliance eval",
                "Live Sonnet brand voice calibration eval",
            ],
        )
        self.assertIn("--mock-brand-voice", steps[1].command)
        self.assertTrue(steps[2].spends_llm_tokens)

    def test_demo_smoke_can_skip_live_brand_voice_step(self) -> None:
        steps = build_demo_smoke_steps(skip_live_brand_voice=True)

        self.assertEqual(
            [step.name for step in steps],
            [
                "Backend unit tests",
                "Token-safe red-team compliance eval",
            ],
        )
        self.assertFalse(any(step.spends_llm_tokens for step in steps))

    def test_brand_voice_eval_selects_case_chunks(self) -> None:
        cases = [
            {"id": "case_1"},
            {"id": "case_2"},
            {"id": "case_3"},
        ]

        selected = select_brand_voice_cases(cases, start=2, end=3)

        self.assertEqual(
            [(index, case["id"]) for index, case in selected],
            [(2, "case_2"), (3, "case_3")],
        )

    def test_brand_voice_eval_rejects_invalid_case_selection(self) -> None:
        with self.assertRaises(ValueError):
            select_brand_voice_cases([{"id": "case_1"}], start=3, end=1)

        with self.assertRaises(ValueError):
            select_brand_voice_cases([{"id": "case_1"}], case_ids=["missing"])

    def test_brand_voice_eval_run_uses_mocked_checker(self) -> None:
        def mocked_voice_checker(
            text: str,
            brand_id: str,
            brand_config: dict[str, object],
            channel: str,
        ) -> dict[str, object]:
            del text, brand_config, channel
            status = "ON_VOICE" if brand_id == "tower_28" else "DRIFTED"
            return {
                "voice_status": status,
                "voice_confidence": 0.88,
                "voice_reason": "Mocked calibration reason.",
            }

        with redirect_stdout(StringIO()) as output:
            exit_code = run_brand_voice_eval(
                [
                    "--case-id",
                    "tower28_good_clean_fun_instagram_on_voice",
                    "--case-id",
                    "halfmagic_perfectionist_corrective_drifted",
                    "--compact",
                ],
                voice_checker=mocked_voice_checker,
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("2/2 selected cases passed", output.getvalue())

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

    def test_red_team_eval_selects_case_chunks(self) -> None:
        cases = [{"id": f"case_{index}"} for index in range(1, 6)]

        selected = select_cases(cases, start=2, end=4)

        self.assertEqual(
            selected,
            [
                (2, {"id": "case_2"}),
                (3, {"id": "case_3"}),
                (4, {"id": "case_4"}),
            ],
        )

    def test_red_team_eval_selects_repeated_case_ids(self) -> None:
        cases = [{"id": f"case_{index}"} for index in range(1, 6)]

        selected = select_cases(cases, case_ids=["case_2", "case_5"])

        self.assertEqual(
            selected,
            [
                (2, {"id": "case_2"}),
                (5, {"id": "case_5"}),
            ],
        )

    def test_red_team_eval_rejects_invalid_case_selection(self) -> None:
        cases = [{"id": "case_1"}]

        with self.assertRaises(ValueError):
            select_cases(cases, start=0)

        with self.assertRaises(ValueError):
            select_cases(cases, start=2, end=1)

        with self.assertRaises(ValueError):
            select_cases(cases, case_ids=["missing"])

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

    def test_cors_allows_week2_vercel_preview_origin(self) -> None:
        preview_origin = "https://beautyagent-ai-git-week2-jillk83s-projects.vercel.app"
        response = self.client.options(
            "/generate",
            headers={
                "Origin": preview_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            preview_origin,
        )

    def test_cors_allows_production_vercel_origin(self) -> None:
        production_origin = "https://beautyagent-ai.vercel.app"
        response = self.client.options(
            "/generate",
            headers={
                "Origin": production_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            production_origin,
        )

    def test_health_endpoint_supports_deployment_checks(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_version_endpoint_reports_deploy_context(self) -> None:
        response = self.client.get("/version")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["app"], "beautyagent-ai-backend")
        self.assertEqual(payload["expected_branch"], "main")
        self.assertIn("git_commit", payload)
        self.assertIn("render_service_name", payload)
        self.assertIn("render_external_url", payload)


if __name__ == "__main__":
    unittest.main()
