from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .models.request_models import GenerateRequest
from .models.response_models import GenerateResponse, TopLevelError

app = FastAPI(title="BeautyAgent AI Backend")


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
    del request

    return GenerateResponse(
        results=[],
        error=TopLevelError(
            code="INTERNAL_ERROR",
            message="Generation is not implemented yet.",
            detail="Backend validation is wired. Draft generation starts in a later step.",
        ),
    )
