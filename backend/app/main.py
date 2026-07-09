import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .agent.beauty_agent import generate_mock_response
from .models.request_models import GenerateRequest
from .models.response_models import GenerateResponse, TopLevelError

app = FastAPI(title="BeautyAgent AI Backend")

DEFAULT_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def get_frontend_origins() -> list[str]:
    configured_origins = os.getenv("FRONTEND_ORIGINS")
    if not configured_origins:
        return DEFAULT_FRONTEND_ORIGINS

    return [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]


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


@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    return generate_mock_response(request)
