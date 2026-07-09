"""Pydantic request models for the `/generate` contract."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


BrandId = Literal["tower_28", "half_magic"]
Channel = Literal["tiktok", "instagram", "email"]
MAX_BRIEF_LENGTH = 1000


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brandId: BrandId
    productName: str = Field(..., min_length=1)
    coreActives: str | None = None
    brief: str = Field(..., min_length=1, max_length=MAX_BRIEF_LENGTH)
    channels: list[Channel] = Field(..., min_length=1, max_length=3)

    @field_validator("productName", "brief")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("coreActives")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def reject_duplicate_channels(self) -> "GenerateRequest":
        if len(self.channels) != len(set(self.channels)):
            raise ValueError("channels must not contain duplicates")
        return self
