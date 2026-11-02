"""Веб-сервис: одна страница и один метод API."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse

from .config import ConfigError, load_settings
from .llm import LLMClient, LLMError
from .pipeline import generate_card
from .render import card_to_markdown
from .schemas import InputError, parse_product

STATIC = Path(__file__).parent / "static"
ERROR_STATUS = {"timeout": 504, "rate_limit": 429}

app = FastAPI(title="Помощник для карточек товара")


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status() -> dict:
    """Что настроено. Сам ключ не отдаём, только факт его наличия."""
    try:
        settings = load_settings()
    except ConfigError as exc:
        return {"model": "", "ready": False, "message": str(exc)}
    try:
        settings.check_ready()
    except ConfigError as exc:
        return {"model": settings.model, "ready": False, "message": str(exc)}
    return {"model": settings.model, "ready": True, "message": ""}


# Тело читаем вручную: при плохом JSON FastAPI вернул бы английскую ошибку 422,
# а контент-менеджеру нужно понятное сообщение
@app.post("/api/generate")
async def generate(request: Request) -> JSONResponse:
    raw = await request.body()
    try:
        product = parse_product(raw)
        settings = load_settings()
        settings.check_ready()
    except InputError as exc:
        return _error("bad_input", str(exc), 400)
    except ConfigError as exc:
        return _error("config", str(exc), 500)

    try:
        card = await run_in_threadpool(
            generate_card, product, LLMClient(settings), settings.max_attempts
        )
    except LLMError as exc:
        return _error(exc.code, str(exc), ERROR_STATUS.get(exc.code, 502))

    return JSONResponse({"card": card.model_dump(), "markdown": card_to_markdown(card)})
