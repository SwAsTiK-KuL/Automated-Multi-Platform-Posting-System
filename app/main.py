import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.platforms import build_platforms
from app.schemas import ErrorResponse, PostRequest, PostResponse
from app.services.posting_service import PostingService

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/posting.log", encoding="utf-8")],
)

app = FastAPI(
    title="Automated Multi-Platform Posting System",
    description=(
        "Publishes a short message (max 200 chars, exactly one CTA link) to Telegraph, Mastodon, "
        "Bluesky, Telegram, Discord, GitHub Gist and Hugging Face. Platform selection is internal."
    ),
    version="1.0.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        msg = err.get("msg", "Invalid input").removeprefix("Value error, ")
        field = ".".join(str(p) for p in err.get("loc", []) if p != "body")
        errors.append(f"{field}: {msg}" if field else msg)
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(errors=errors).model_dump(),
    )


def get_posting_service(settings: Settings = Depends(get_settings)) -> PostingService:
    return PostingService(settings, build_platforms(settings))


@app.get("/health", tags=["meta"])
async def health(settings: Settings = Depends(get_settings)) -> dict:
    platforms = build_platforms(settings)
    return {
        "status": "ok",
        "platforms": {p.name: ("configured" if not p.missing_settings() else f"missing {', '.join(p.missing_settings())}")
                      for p in platforms},
    }


@app.post(
    "/posting",
    response_model=PostResponse,
    responses={422: {"model": ErrorResponse, "description": "Validation error"}},
    tags=["posting"],
)
async def create_posting(payload: PostRequest, service: PostingService = Depends(get_posting_service)) -> PostResponse:
    return await service.post(payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=4000)
