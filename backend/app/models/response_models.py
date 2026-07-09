"""Pydantic response models for the `/generate` contract."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .request_models import Channel


GenerationStatus = Literal["completed", "error"]
ComplianceStatus = Literal["PASSED", "FAILED"]
DetectionSource = Literal["deterministic", "llm_audit", "both"]
TopLevelErrorCode = Literal["VALIDATION_ERROR", "RATE_LIMITED", "INTERNAL_ERROR"]
ChannelErrorCode = Literal["TIMEOUT", "RATE_LIMITED", "TOOL_ERROR"]


class ChannelError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ChannelErrorCode
    message: str


class TopLevelError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: TopLevelErrorCode
    message: str
    detail: str | None = None


class ChannelResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Channel
    generation_status: GenerationStatus
    raw_draft: str | None
    compliance_status: ComplianceStatus | None
    flagged_phrases: list[str] | None
    explanation: str | None
    detection_source: DetectionSource | None
    final_safe_output: str | None
    retry_exhausted: bool | None
    error: ChannelError | None


class GenerateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[ChannelResult]
    error: TopLevelError | None
