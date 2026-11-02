"""Проверки до LLM: полнота данных, инъекции, противоречия, таблица характеристик."""

import re
from dataclasses import dataclass, field

from .facts import InputIndex, extract_facts, normalize
from .schemas import MISSING, Characteristic, MissingField, ProductInput, is_empty

# Базовые поля из задания. Если их нет, пишем «данных нет» и не гадаем, применимы ли они
BASE_FIELDS = {
    "диапазон измерения": r"диапазон\w*\s+(?:измер|показ)|предел\w*\s+измер|^диапазон$",
    "класс точности": r"класс\w*\s+точност",
    "питание": r"питани",
    "тип корпуса": r"тип\w*\s+корпус|исполнени\w*\s+корпус|^корпус\w*$",
    "интерфейсы": r"интерфейс|протокол",
}

INJECTION_RE = re.compile(
    r"игнорир|забудь|не\s+обращай\s+внимани|отмени\w*\s+(?:правил|инструкц)|"
    r"системн\w+\s+(?:промпт|инструкц|сообщени)|предыдущ\w+\s+(?:инструкц|правил)|"
    r"ты\s+теперь|твоя\s+новая\s+задача|нов\w+\s+инструкц|напиши,?\s+что|укажи,?\s+что|"
    r"ignore\s+(?:all|any|previous|prior|above|the)|disregard|system\s+prompt|you\s+are\s+now|"
    r"new\s+instructions|jailbreak|<\s*/?\s*(?:system|assistant|product_data)",
    re.IGNORECASE,
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
WINDOW_STOP_RE = re.compile(
    r";|\.\s|,\s+[а-яa-z]|\s(?:и|при|для|с|со|по|на|в|во|а|но)\s", re.IGNORECASE
)

MAX_DESCRIPTION_CHARS = 4000


@dataclass
class Contradiction:
    key: str
    spec_value: str
    description_fragment: str
    keys: set[str] = field(default_factory=set)


@dataclass
class Precheck:
    """Результат проверок: что отдать модели и что показать контент-менеджеру."""

    product: ProductInput  # очищенные данные, именно они уходят в модель
    characteristics: list[Characteristic]
    missing_fields: list[MissingField]
    warnings: list[str]
    contradictions: list[Contradiction]
    index: InputIndex
    insufficient: bool
    needs_review: bool


def _has_letters(text: str) -> bool:
    return len(re.findall(r"[A-Za-zА-Яа-яЁё]", text)) >= 3


def remove_injections(text: str) -> tuple[str, list[str]]:
    """Убирает предложения, похожие на инструкции для модели. Числа из них не считаем данными."""
    kept, removed = [], []
    for sentence in SENTENCE_SPLIT_RE.split(text):
        (removed if INJECTION_RE.search(sentence) else kept).append(sentence)
    return " ".join(part for part in kept if part.strip()), removed


def truncate_description(text: str) -> tuple[str, bool]:
    """Ограничивает длину текста для модели. Обрезку не скрываем: об этом будет предупреждение."""
    if len(text) <= MAX_DESCRIPTION_CHARS:
        return text, False
    cut = text.rfind(". ", 0, MAX_DESCRIPTION_CHARS)
    return text[: cut + 1 if cut > 0 else MAX_DESCRIPTION_CHARS], True


def _key_pattern(key: str) -> re.Pattern | None:
    """«диапазон измерений» находит и «диапазон измерения»: сравниваем основы слов."""
    words = re.findall(r"[а-яa-z]{3,}", key.split(",")[0].lower())
    if not words:
        return None
    stems = [word[: max(4, len(word) - 2)] + r"\w*" for word in words]
    return re.compile(r"\s+".join(stems), re.IGNORECASE)


def find_contradictions(specs: dict[str, str], description: str) -> list[Contradiction]:
    """Ищет в описании поле из specs и сравнивает значение рядом с ним."""
    text = normalize(description)
    result = []
    for key, value in specs.items():
        pattern = _key_pattern(key)
        if pattern is None:
            continue
        spec_facts = extract_facts(normalize(value))
        spec_keys = {f.key for f in spec_facts if f.kind in ("number", "code", "standard")}
        for match in pattern.finditer(text):
            rest = text[match.end() : match.end() + 80]
            stop = WINDOW_STOP_RE.search(rest)
            window = rest[: stop.start()] if stop else rest
            found = {
                f.key for f in extract_facts(window) if f.kind in ("number", "code", "standard")
            }
            conflict = bool(found - spec_keys) if found else _word_conflict(window, value)
            if conflict:
                fragment = (match.group() + window).strip()
                result.append(Contradiction(key, value, fragment, (found | spec_keys)))
                break
    return result


def _word_conflict(window: str, value: str) -> bool:
    """Текстовые значения: «тип корпуса: настенный» при «щитовой» в specs.
    Сравниваем только при явном разделителе, иначе много ложных срабатываний."""
    match = re.match(r"\s*[:-]\s*([а-яa-zё]{4,})", window, re.IGNORECASE)
    if not match or extract_facts(normalize(value)):
        return False
    return match.group(1).lower()[:4] not in normalize(value).lower()


def run_precheck(product: ProductInput) -> Precheck:
    warnings: list[str] = []
    missing: list[MissingField] = []
    review = False

    name = product.name.strip()
    manufacturer = "" if is_empty(product.manufacturer) else product.manufacturer.strip()
    full_description = "" if is_empty(product.description) else product.description.strip()

    for label, value in (("name", name), ("manufacturer", manufacturer)):
        if INJECTION_RE.search(value):
            warnings.append(f"В поле {label} есть текст, похожий на инструкцию для модели.")
            review = True

    full_description, removed = remove_injections(full_description)
    if removed:
        review = True
        warnings.append(
            "В описании есть текст, похожий на инструкцию для модели. Он не передан модели "
            f"и не считается данными: «{removed[0].strip()[:150]}»."
        )

    # Значения specs делим на годные, пустые и подозрительные
    specs: dict[str, str] = {}
    empty_keys = []
    for key, value in product.specs.items():
        if is_empty(key):
            continue
        if is_empty(value):
            empty_keys.append(key.strip())
        elif INJECTION_RE.search(value) or INJECTION_RE.search(key):
            review = True
            empty_keys.append(key.strip())
            warnings.append(
                f"Значение «{key.strip()}» похоже на инструкцию для модели и не использовано."
            )
        else:
            specs[key.strip()] = value.strip()

    contradictions = find_contradictions(specs, full_description)
    conflicts = {item.key: item for item in contradictions}
    for item in contradictions:
        review = True
        warnings.append(
            f"Противоречие: в specs «{item.key}» = «{item.spec_value}», "
            f"а в описании «{item.description_fragment}». Значение не выбрано, уточните."
        )

    # Оба спорных значения прячем от модели: она не сможет выбрать одно из них сама
    model_specs = {key: value for key, value in specs.items() if key not in conflicts}
    model_description = _without_fragments(
        full_description, [item.description_fragment for item in contradictions]
    )
    description, truncated = truncate_description(model_description)
    if truncated:
        warnings.append(
            f"Описание длиннее {MAX_DESCRIPTION_CHARS} символов. Модель получила только начало "
            f"({len(description)} из {len(model_description)}). Проверьте, что важное не потеряно."
        )

    characteristics = []
    for key, value in specs.items():
        if key in conflicts:
            characteristics.append(
                Characteristic(
                    name=key,
                    value=f"противоречие: «{value}» или «{conflicts[key].description_fragment}»",
                    source=f"specs.{key} и description",
                    status="conflict",
                    note="Значение не выбрано, уточните по паспорту.",
                )
            )
        else:
            characteristics.append(Characteristic(name=key, value=value, source=f"specs.{key}"))

    for key in empty_keys:
        if not any(re.search(pattern, key.lower()) for pattern in BASE_FIELDS.values()):
            characteristics.append(
                Characteristic(
                    name=key, value=MISSING, source="specs: поле пустое", status="missing",
                    note="Уточнить.",
                )
            )
            missing.append(MissingField(field=key, reason="поле в specs пустое"))

    for base_name, pattern in BASE_FIELDS.items():
        if any(re.search(pattern, key.lower()) for key in specs):
            continue
        fragment = _mention(pattern, full_description)
        if fragment:
            characteristics.append(
                Characteristic(
                    name=base_name, value=f"{MISSING} в specs", source="description",
                    status="check", note=f"Упомянуто в описании: «{fragment}». Проверьте.",
                )
            )
            missing.append(MissingField(field=base_name, reason="есть только в описании"))
        else:
            characteristics.append(
                Characteristic(
                    name=base_name, value=MISSING, source="нет во входе", status="missing",
                    note="Уточнить. Нет данных, это не значит, что поле неприменимо.",
                )
            )
            missing.append(MissingField(field=base_name, reason="нет во входных данных"))

    if not manufacturer:
        missing.append(MissingField(field="производитель", reason="не указан"))
    if not specs:
        missing.append(MissingField(field="характеристики (specs)", reason="нет значений"))
    if not full_description:
        missing.append(MissingField(field="описание", reason="не указано"))

    insufficient = False
    if not _has_letters(name):
        insufficient = True
        missing.insert(0, MissingField(field="название", reason="пустое или это не название"))
    if not specs and not _has_letters(full_description):
        insufficient = True

    sources = {"name": name, "manufacturer": manufacturer}
    for key, value in model_specs.items():
        sources[f"specs.{key}"] = _spec_source_text(key, value)
    sources["description"] = description

    return Precheck(
        product=ProductInput(
            name=name, manufacturer=manufacturer, specs=model_specs, description=description
        ),
        characteristics=characteristics,
        missing_fields=missing,
        warnings=warnings,
        contradictions=contradictions,
        index=InputIndex(sources),
        insufficient=insufficient,
        needs_review=review,
    )


def _without_fragments(text: str, fragments: list[str]) -> str:
    """Убирает предложения со спорными значениями."""
    if not fragments:
        return text
    sentences = SENTENCE_SPLIT_RE.split(text)
    return " ".join(s for s in sentences if not any(f in normalize(s) for f in fragments))


def _spec_source_text(key: str, value: str) -> str:
    """«давление, МПа: 1,6» значит 1,6 МПа: единица стоит в названии поля."""
    if "," in key and not re.search(r"[^\d\s.,+-]", value.replace("...", "")):
        return f"{key}: {value} {key.rsplit(',', 1)[1].strip()}"
    return f"{key}: {value}"


def _mention(pattern: str, description: str) -> str:
    # ^...$ в шаблоне рассчитаны на название поля, в описании ищем только обычные части
    usable = "|".join(part for part in pattern.split("|") if not part.startswith("^"))
    match = re.search(usable, description, re.IGNORECASE)
    if not match:
        return ""
    return description[max(0, match.start() - 20) : match.end() + 50].strip()
