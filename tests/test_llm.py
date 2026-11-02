import httpx
import pytest

from card_assistant.config import ConfigError, Settings, load_settings
from card_assistant.llm import LLMClient, LLMError

OK = {
    "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
    "usage": {"total_tokens": 42},
}
SECRET = "sk-very-secret-value"


def make_client(handler) -> tuple[LLMClient, list[float]]:
    pauses: list[float] = []
    client = LLMClient(
        Settings(base_url="https://api.test/v1", model="m", api_key=SECRET), sleep=pauses.append
    )
    client._http = httpx.Client(transport=httpx.MockTransport(handler))
    return client, pauses


def sequence(*responses):
    items = list(responses)

    def handler(request):
        item = items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return handler


def test_success_returns_content_and_sends_key_in_header():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        return httpx.Response(200, json=OK)

    client, _ = make_client(handler)
    reply = client.complete([])
    assert reply.total_tokens == 42
    assert seen["auth"] == f"Bearer {SECRET}"
    assert seen["url"] == "https://api.test/v1/chat/completions"


@pytest.mark.parametrize(
    "status, code, text",
    [(401, "auth", "ключ"), (403, "auth", "ключ"), (402, "payment", "средства"),
     (404, "not_found", "Модель"), (400, "bad_request", "отклонил")],
)  # fmt: skip
def test_errors_that_are_not_retried(status, code, text):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": "details"})

    client, pauses = make_client(handler)
    with pytest.raises(LLMError) as error:
        client.complete([])
    assert error.value.code == code
    assert text in str(error.value)
    assert len(calls) == 1
    assert pauses == []


def test_429_retries_and_respects_retry_after():
    client, pauses = make_client(
        sequence(
            httpx.Response(429, headers={"retry-after": "7"}),
            httpx.Response(429, headers={"retry-after": "9999"}),
            httpx.Response(200, json=OK),
        )
    )
    assert client.complete([]).total_tokens == 42
    assert pauses == [7.0, 30.0]


def test_5xx_retries_then_gives_russian_error():
    client, pauses = make_client(sequence(*[httpx.Response(503)] * 3))
    with pytest.raises(LLMError, match="временно недоступен") as error:
        client.complete([])
    assert error.value.code == "server"
    assert pauses == [2.0, 5.0]


def test_5xx_then_success():
    client, _ = make_client(sequence(httpx.Response(500), httpx.Response(200, json=OK)))
    assert client.complete([]).content == "{}"


def test_timeout_is_retried_then_reported():
    client, pauses = make_client(sequence(*[httpx.ReadTimeout("slow")] * 3))
    with pytest.raises(LLMError, match="не ответила") as error:
        client.complete([])
    assert error.value.code == "timeout"
    assert len(pauses) == 2


def test_connection_error_is_reported():
    client, _ = make_client(sequence(*[httpx.ConnectError("no route")] * 3))
    with pytest.raises(LLMError, match="подключиться"):
        client.complete([])


def test_unknown_response_format():
    client, _ = make_client(sequence(httpx.Response(200, json={"foo": 1})))
    with pytest.raises(LLMError, match="неизвестном формате"):
        client.complete([])


def test_key_is_not_in_error_text_or_repr():
    client, _ = make_client(sequence(httpx.Response(401, text=SECRET)))
    with pytest.raises(LLMError) as error:
        client.complete([])
    assert SECRET not in str(error.value)
    assert SECRET not in repr(client.settings)


def test_cloud_without_key_gives_clear_error():
    settings = Settings(base_url="https://api.deepseek.com", model="m")
    with pytest.raises(ConfigError, match="LLM_API_KEY"):
        settings.check_ready()


def test_local_model_needs_no_key():
    Settings(base_url="http://localhost:11434/v1", model="m").check_ready()
    Settings(base_url="http://host.docker.internal:11434/v1", model="m").check_ready()


def test_bad_extra_body_gives_clear_error(monkeypatch):
    monkeypatch.setenv("LLM_EXTRA_BODY", "{битый")
    with pytest.raises(ConfigError, match="LLM_EXTRA_BODY"):
        load_settings("несуществующий.env")
