"""Модели данных: вход, ответ модели, итоговая карточка."""

import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

MISSING = "данных нет"
QUERIES_NOTE = "Гипотезы модели. Частотность по Wordstat не проверялась."
MAX_INPUT_BYTES = 1_000_000

# Такие значения считаем отсутствующими: контент-менеджеры часто ставят прочерк
EMPTY_VALUES = {
    "", "-", "--", "—", "–", "?", "н/д", "нд", "n/a", "na", "null", "none",
    "данных нет", "нет данных", "не указано", "уточнить", "tbd",
}  # fmt: skip


class InputError(Exception):
    """Некорректный вход. Текст сообщения показываем пользователю."""


def is_empty(value: str) -> bool:
    return value.strip().lower() in EMPTY_VALUES


class ProductInput(BaseModel):
    name: str = ""
    manufacturer: str = ""
    specs: dict[str, str] = Field(default_factory=dict)
    description: str = ""

    @field_validator("name", "manufacturer", "description", mode="before")
    @classmethod
    def text_or_empty(cls, value):
        if value is None:
            return ""
        if isinstance(value, bool) or not isinstance(value, str | int | float):
            raise ValueError("ожидается текст")
        return str(value)

    @field_validator("specs", mode="before")
    @classmethod
    def specs_to_text(cls, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("ожидается словарь вида {характеристика: значение}")
        result = {}
        for key, item in value.items():
            if item is None:
                item = ""
            elif isinstance(item, list):
                item = ", ".join(str(part) for part in item)
            elif isinstance(item, bool) or not isinstance(item, str | int | float):
                raise ValueError(f"значение «{key}» должно быть текстом или числом")
            result[str(key)] = str(item)
        return result


def parse_product(raw: str | bytes) -> ProductInput:
    """Разбирает JSON товара. При ошибке бросает InputError с понятным текстом."""
    if len(raw) > MAX_INPUT_BYTES:
        raise InputError("Вход слишком большой: допускается не больше 1 МБ.")
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InputError("Файл не в кодировке UTF-8. Сохраните его в UTF-8.") from exc
    raw = raw.lstrip("﻿")
    if not raw.strip():
        raise InputError("Вход пустой. Нужен JSON с полями name, manufacturer, specs, description.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError(
            f"Некорректный JSON: ошибка в строке {exc.lineno}, символ {exc.colno}."
        ) from exc
    if not isinstance(data, dict):
        raise InputError(
            "Ожидается один товар: JSON-объект с полями name, manufacturer, specs, description."
        )
    try:
        return ProductInput.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg'].removeprefix('Value error, ')}"
            for err in exc.errors()
        )
        raise InputError(f"Неверный формат полей. {problems}.") from exc


class CommercialBlock(BaseModel):
    suitable_for: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class LLMDraft(BaseModel):
    """То, что возвращает модель. Длины здесь не проверяем: это делает validator.py,
    чтобы модель получила понятную ошибку при повторе."""

    seo_title: str
    seo_description: str
    search_queries: list[str]
    commercial: CommercialBlock


class Characteristic(BaseModel):
    name: str
    value: str
    source: str
    status: Literal["ok", "missing", "conflict", "check"] = "ok"
    note: str = ""


class MissingField(BaseModel):
    field: str
    reason: str


class Issue(BaseModel):
    code: str
    field: str
    message: str
    value: str = ""


class FactTrace(BaseModel):
    """Откуда взято значение из сгенерированного текста."""

    value: str
    used_in: str
    source: str
    snippet: str = ""


class AttemptLog(BaseModel):
    number: int
    issues: list[Issue]
    seconds: float
    total_tokens: int = 0


class Card(BaseModel):
    status: Literal["ready", "needs_review", "insufficient_data"]
    name: str
    manufacturer: str
    seo_title: str = ""
    seo_title_length: int = 0
    seo_description: str = ""
    seo_description_length: int = 0
    characteristics: list[Characteristic] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    search_queries_note: str = QUERIES_NOTE
    commercial: CommercialBlock = Field(default_factory=CommercialBlock)
    missing_fields: list[MissingField] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    traces: list[FactTrace] = Field(default_factory=list)
    model: str = ""
    attempts: list[AttemptLog] = Field(default_factory=list)
