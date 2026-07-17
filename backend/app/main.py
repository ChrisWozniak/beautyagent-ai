import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .agent.beauty_agent import generate_mock_response, load_brand_configs
from .config_loader import ConfigLoadError
from .models.request_models import BrandId, Channel, GenerateRequest
from .models.response_models import GenerateResponse, TopLevelError
from .tools.check_brand_voice import check_brand_voice

app = FastAPI(title="BeautyAgent AI Backend")

APP_NAME = "beautyagent-ai-backend"
EXPECTED_RENDER_BRANCH = "main"

DEFAULT_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://beautyagent-ai.vercel.app",
    "https://beautyagent-ai-git-week2-jillk83s-projects.vercel.app",
]


def get_frontend_origins() -> list[str]:
    configured_origins = os.getenv("FRONTEND_ORIGINS")
    if not configured_origins:
        return DEFAULT_FRONTEND_ORIGINS

    configured = [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]
    return list(dict.fromkeys([*DEFAULT_FRONTEND_ORIGINS, *configured]))


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_frontend_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def validation_error_response(detail: str) -> GenerateResponse:
    return GenerateResponse(
        results=[],
        error=TopLevelError(
            code="VALIDATION_ERROR",
            message="Invalid request.",
            detail=detail,
        ),
    )


def internal_error_response(detail: str | None = None) -> GenerateResponse:
    return GenerateResponse(
        results=[],
        error=TopLevelError(
            code="INTERNAL_ERROR",
            message="Internal server error.",
            detail=detail,
        ),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    del request

    error_messages = []
    for error in exc.errors():
        field_path = ".".join(str(part) for part in error["loc"] if part != "body")
        message = error["msg"]
        error_messages.append(f"{field_path}: {message}" if field_path else message)

    response = validation_error_response("; ".join(error_messages))
    return JSONResponse(status_code=400, content=response.model_dump())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    return {
        "status": "ok",
        "app": APP_NAME,
        "expected_branch": EXPECTED_RENDER_BRANCH,
        "git_commit": (
            os.getenv("RENDER_GIT_COMMIT")
            or os.getenv("GIT_COMMIT")
            or os.getenv("COMMIT_SHA")
            or "unknown"
        ),
        "render_service_name": os.getenv("RENDER_SERVICE_NAME", "unknown"),
        "render_external_url": os.getenv("RENDER_EXTERNAL_URL", "unknown"),
    }


class EvaluateVoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    brandId: BrandId
    channel: Channel
    text: str = Field(..., min_length=1)


@app.post("/evaluate-voice")
async def evaluate_voice(request: EvaluateVoiceRequest) -> dict[str, Any]:
    brand_configs = load_brand_configs()
    brand_config = brand_configs[request.brandId]
    return check_brand_voice(
        text=request.text,
        brand_id=request.brandId,
        brand_config=brand_config,
        channel=request.channel,
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    try:
        return await generate_mock_response(request)
    except ConfigLoadError as exc:
        response = internal_error_response(str(exc))
        return JSONResponse(status_code=500, content=response.model_dump())
    except Exception:
        response = internal_error_response()
        return JSONResponse(status_code=500, content=response.model_dump())
