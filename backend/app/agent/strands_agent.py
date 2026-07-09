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
    """Thin wrapper around the channel loop for future Strands orchestration."""

    def run_channel(self, request: GenerateRequest, channel: Channel) -> ChannelResult:
        return process_channel_loop(request, channel)

    @property
    def tools(self) -> list[object]:
        return [check_compliance_tool]


def build_strands_adapter() -> BeautyAgentStrandsAdapter:
    return BeautyAgentStrandsAdapter()
