"""Главный сценарий: проверки до модели, генерация с повторами, проверки после модели."""

import json
import re
import time

from pydantic import ValidationError

from .llm import LLMClient, LLMError
from .precheck import Precheck, run_precheck
from .prompts import SYSTEM_PROMPT, build_retry_message, build_user_message
from .schemas import AttemptLog, Card, FactTrace, Issue, LLMDraft, ProductInput
from .validator import check_facts, check_structure


def parse_draft(content: str, finish_reason: str = "") -> LLMDraft | Issue:
    """Разбирает ответ модели. Вместо исключения возвращает Issue, чтобы повторить запрос."""
    if finish_reason == "length":
        return _json_issue("ответ оборвался на лимите токенов. Пиши короче.")
    text = content.strip()
    # Маленькие модели любят оборачивать JSON в ```json
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    if not text:
        return _json_issue("ответ пустой. Верни объект JSON.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _json_issue("ответ не является корректным JSON. Верни только объект JSON.")
    try:
        return LLMDraft.model_validate(data)
    except ValidationError as exc:
        problems = ", ".join(".".join(str(p) for p in err["loc"]) for err in exc.errors())
        return _json_issue(f"в JSON отсутствуют или неверны поля: {problems}.")


def _json_issue(message: str) -> Issue:
    return Issue(code="invalid_json", field="ответ модели", message=message)


def generate_card(product: ProductInput, client: LLMClient, max_attempts: int = 3) -> Card:
    """Строит карточку. Ошибку API пробрасывает только если нет ни одного черновика."""
    pre = run_precheck(product)
    if pre.insufficient:
        return _base_card(pre, "insufficient_data", client.settings.model)

    user_message = build_user_message(pre.product, pre.contradictions)
    previous_content = ""
    previous_issues: list[Issue] = []
    attempts: list[AttemptLog] = []
    best: tuple[LLMDraft, list[Issue], list[FactTrace]] | None = None
    warnings = list(pre.warnings)

    for number in range(1, max_attempts + 1):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        # Передаём только последнюю попытку: у локальных моделей маленькое окно контекста
        if previous_issues:
            messages += [
                {"role": "assistant", "content": previous_content},
                {"role": "user", "content": build_retry_message(previous_issues)},
            ]

        started = time.perf_counter()
        try:
            reply = client.complete(messages)
        except LLMError as exc:
            if best is None:
                raise
            warnings.append(f"Повтор {number} не выполнен: {exc} Показан лучший черновик.")
            break
        seconds = round(time.perf_counter() - started, 1)

        parsed = parse_draft(reply.content, reply.finish_reason)
        if isinstance(parsed, Issue):
            issues, traces = [parsed], []
        else:
            fact_issues, traces = check_facts(parsed, pre.index, pre.contradictions)
            issues = check_structure(parsed) + fact_issues
            if best is None or len(issues) < len(best[1]):
                best = (parsed, issues, traces)

        attempts.append(
            AttemptLog(
                number=number, issues=issues, seconds=seconds, total_tokens=reply.total_tokens
            )
        )
        if not issues:
            break
        previous_content, previous_issues = reply.content, issues

    card = _base_card(pre, "needs_review", client.settings.model)
    card.warnings = warnings
    card.attempts = attempts
    if best is None:
        # Ни один ответ не разобрался: таблица и пробелы в данных всё равно полезны
        card.issues = attempts[-1].issues
        return card

    draft, issues, traces = best
    card.seo_title = draft.seo_title
    card.seo_title_length = len(draft.seo_title)
    card.seo_description = draft.seo_description
    card.seo_description_length = len(draft.seo_description)
    card.search_queries = draft.search_queries
    card.commercial = draft.commercial
    card.issues = issues
    card.traces = traces
    if not issues and not pre.needs_review:
        card.status = "ready"
    return card


def _base_card(pre: Precheck, status: str, model: str) -> Card:
    return Card(
        status=status,
        name=pre.product.name,
        manufacturer=pre.product.manufacturer,
        characteristics=pre.characteristics,
        missing_fields=pre.missing_fields,
        warnings=pre.warnings,
        model=model,
    )
