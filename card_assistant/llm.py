"""Клиент OpenAI-совместимого API. Один код работает с облачной моделью и с Ollama."""

import time
from dataclasses import dataclass

import httpx

from .config import Settings

MAX_TOKENS = 2000
RETRY_PAUSES = (2.0, 5.0)  # паузы между повторами при таймауте, 429 и 5xx
MAX_RETRY_AFTER = 30.0


class LLMError(Exception):
    """Ошибка обращения к модели. Текст сообщения показываем пользователю."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class LLMReply:
    content: str
    finish_reason: str
    total_tokens: int


class LLMClient:
    def __init__(self, settings: Settings, sleep=time.sleep):
        self.settings = settings
        self._sleep = sleep
        self._http = httpx.Client(timeout=settings.timeout_seconds)

    def complete(self, messages: list[dict]) -> LLMReply:
        """Отправляет запрос. Повторяем только то, что может пройти со второго раза."""
        pauses = list(RETRY_PAUSES)
        while True:
            try:
                return self._request(messages)
            except _Retryable as exc:
                if not pauses:
                    raise exc.error from None
                self._sleep(exc.retry_after or pauses[0])
                pauses.pop(0)

    def _request(self, messages: list[dict]) -> LLMReply:
        settings = self.settings
        # У Ollama ключа нет, но заголовок должен быть непустым
        headers = {"Authorization": f"Bearer {settings.api_key or 'local'}"}
        body = {
            "model": settings.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": MAX_TOKENS,
            "response_format": {"type": "json_object"},
            **settings.extra_body,
        }
        try:
            response = self._http.post(
                f"{settings.base_url}/chat/completions", json=body, headers=headers
            )
        except httpx.TimeoutException:
            raise _Retryable(
                LLMError(
                    f"Модель не ответила за {settings.timeout_seconds:.0f} секунд. "
                    "Попробуйте ещё раз или увеличьте LLM_TIMEOUT_SECONDS.",
                    "timeout",
                )
            ) from None
        except httpx.HTTPError:
            raise _Retryable(
                LLMError(
                    f"Не удалось подключиться к {settings.base_url}. "
                    "Проверьте интернет или запущена ли Ollama.",
                    "connection",
                )
            ) from None

        self._raise_for_status(response)
        return self._parse(response)

    def _raise_for_status(self, response: httpx.Response) -> None:
        status = response.status_code
        if status == 200:
            return
        if status in (401, 403):
            raise LLMError("Сервис модели не принял ключ API. Проверьте LLM_API_KEY.", "auth")
        if status == 402:
            raise LLMError("На счёте сервиса модели закончились средства.", "payment")
        if status == 404:
            raise LLMError(
                f"Модель «{self.settings.model}» или адрес API не найдены. "
                "Проверьте LLM_MODEL и LLM_BASE_URL.",
                "not_found",
            )
        if status == 429:
            raise _Retryable(
                LLMError("Превышен лимит запросов к модели. Подождите минуту.", "rate_limit"),
                retry_after=_retry_after(response),
            )
        if status >= 500:
            raise _Retryable(
                LLMError(f"Сервис модели временно недоступен (ошибка {status}).", "server")
            )
        raise LLMError(
            f"Сервис модели отклонил запрос (ошибка {status}). "
            "Проверьте LLM_MODEL и LLM_EXTRA_BODY.",
            "bad_request",
        )

    @staticmethod
    def _parse(response: httpx.Response) -> LLMReply:
        try:
            data = response.json()
            choice = data["choices"][0]
            return LLMReply(
                content=choice["message"].get("content") or "",
                finish_reason=choice.get("finish_reason") or "",
                total_tokens=(data.get("usage") or {}).get("total_tokens", 0),
            )
        except (ValueError, KeyError, IndexError, TypeError):
            raise LLMError(
                "Сервис модели вернул ответ в неизвестном формате.", "bad_response"
            ) from None


class _Retryable(Exception):
    def __init__(self, error: LLMError, retry_after: float | None = None):
        self.error = error
        self.retry_after = retry_after


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return min(float(response.headers["retry-after"]), MAX_RETRY_AFTER)
    except (KeyError, ValueError):
        return None
