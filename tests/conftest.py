"""Фейковый клиент модели: тесты не ходят в сеть и не требуют ключа."""

import json

import pytest

from card_assistant.config import Settings
from card_assistant.llm import LLMError, LLMReply
from card_assistant.schemas import ProductInput

MANOMETER = {
    "name": "Манометр показывающий DM 02",
    "manufacturer": "Манотомь",
    "specs": {
        "диапазон измерений": "0–1,6 МПа",
        "класс точности": "1,5",
        "присоединение": "G1/2",
        "диаметр корпуса": "100 мм",
    },
    "description": "Прибор предназначен для измерения избыточного давления.",
}

GOOD_SENTENCE = (
    "Манометр показывающий DM 02 производства Манотомь предназначен для измерения "
    "избыточного давления, диапазон измерений 0-1,6 МПа, класс точности 1,5. "
)


def good_draft(**overrides) -> dict:
    draft = {
        "seo_title": "Манометр показывающий DM 02 Манотомь, 0-1,6 МПа",
        "seo_description": (GOOD_SENTENCE * 7)[:1000],
        "search_queries": ["манометр DM 02", "манометр G1/2", "манометр 1,6 МПа"],
        "commercial": {
            "suitable_for": ["Тем, кому нужно измерять избыточное давление"],
            "tasks": ["Измерение избыточного давления"],
            "assumptions": [],
        },
    }
    draft.update(overrides)
    return draft


class FakeClient:
    """Отдаёт заранее заданные ответы и запоминает, что у него спросили."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []
        self.settings = Settings(base_url="http://localhost/v1", model="fake")

    def complete(self, messages):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, LLMError):
            raise reply
        content = reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)
        return LLMReply(content=content, finish_reason="stop", total_tokens=10)


@pytest.fixture
def manometer() -> ProductInput:
    return ProductInput.model_validate(MANOMETER)
