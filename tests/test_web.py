from conftest import MANOMETER, FakeClient, good_draft
from fastapi.testclient import TestClient

from card_assistant import web
from card_assistant.config import Settings
from card_assistant.llm import LLMError

SECRET = "sk-very-secret-value"


def setup(monkeypatch, *replies):
    settings = Settings(base_url="https://api.test/v1", model="fake", api_key=SECRET)
    monkeypatch.setattr(web, "load_settings", lambda: settings)
    monkeypatch.setattr(web, "LLMClient", lambda _settings: FakeClient(*replies))
    return TestClient(web.app)


def test_page_opens(monkeypatch):
    response = setup(monkeypatch).get("/")
    assert response.status_code == 200
    assert "<title>" in response.text


def test_generate_returns_card_and_markdown(monkeypatch):
    response = setup(monkeypatch, good_draft()).post("/api/generate", json=MANOMETER)
    assert response.status_code == 200
    assert response.json()["card"]["status"] == "ready"
    assert "## Характеристики" in response.json()["markdown"]
    assert SECRET not in response.text


def test_bad_json_gives_400_in_russian(monkeypatch):
    response = setup(monkeypatch).post("/api/generate", content="{битый json")
    assert response.status_code == 400
    assert "Некорректный JSON" in response.json()["error"]["message"]


def test_api_error_has_no_traceback(monkeypatch):
    error = LLMError("Сервис модели не принял ключ API.", "auth")
    response = setup(monkeypatch, error).post("/api/generate", json=MANOMETER)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "auth"
    assert "Traceback" not in response.text


def test_status_does_not_expose_key(monkeypatch):
    response = setup(monkeypatch).get("/api/status")
    assert response.json()["ready"] is True
    assert SECRET not in response.text
