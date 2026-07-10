"""Strands-compatible adapter for the BeautyAgent backend loop.

The existing deterministic loop remains the source of truth for the MVP
contract. This adapter gives the project a Strands integration point without
changing `/generate` behavior or requiring Strands during local tests.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models.request_models import Channel, GenerateRequest
from ..models.response_models import ChannelResult
from ..tools.check_compliance import check_compliance_tool
from .beauty_agent import process_channel_loop


@dataclass
class BeautyAgentStrandsAdapter:
    """Thin wrapper exposing the backend loop and Strands tool surface."""

    def run_channel(self, request: GenerateRequest, channel: Channel) -> ChannelResult:
        return process_channel_loop(request, channel)

    @property
    def tools(self) -> list[object]:
        return [check_compliance_tool]

    @property
    def tool_names(self) -> list[str]:
        return [
            getattr(tool, "tool_name", getattr(tool, "__name__", type(tool).__name__))
            for tool in self.tools
        ]

    def integration_summary(self) -> dict[str, object]:
        return {
            "agent_loop": "process_channel_loop",
            "contract_source": "/generate response models",
            "tools": self.tool_names,
            "deterministic_backstop": True,
        }


def build_strands_adapter() -> BeautyAgentStrandsAdapter:
    return BeautyAgentStrandsAdapter()
