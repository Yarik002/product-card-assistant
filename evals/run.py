"""Прогон набора случаев на настоящей модели.

  python -m evals.run --label deepseek-flash
  python -m evals.run --env-file .env.ollama --label qwen2.5-3b

Результат: evals/results/<label>.json (всё, включая тексты) и evals/results/<label>.md (отчёт).
"""

import argparse
import json
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

from card_assistant.config import ConfigError, load_settings
from card_assistant.facts import normalize
from card_assistant.llm import LLMClient, LLMError
from card_assistant.pipeline import generate_card
from card_assistant.schemas import Card, InputError, parse_product

from .cases import CASES

RESULTS_DIR = Path(__file__).parent / "results"
# Всё это означает, что модель написала факт, которого нет во входе
FABRICATION_CODES = {
    "invented_number",
    "invented_unit",
    "invented_code",
    "invented_standard",
    "invented_name",
    "conflicting_value",
    "unconfirmed_claim",
    "evaluative_claim",
}


def generated_text(card: Card) -> str:
    commercial = card.commercial
    parts = [card.seo_title, card.seo_description, *card.search_queries]
    parts += [*commercial.suitable_for, *commercial.tasks, *commercial.assumptions]
    return "\n".join(parts)


def run_case(case: dict, client, max_attempts: int) -> dict:
    expect = case["expect"]
    result = {"id": case["id"], "title": case["title"], "failures": [], "leaks": []}
    started = time.perf_counter()

    raw = case.get("raw") or json.dumps(case["input"], ensure_ascii=False)
    try:
        product = parse_product(raw)
    except InputError as exc:
        result["status"] = "input_error"
        result["message"] = str(exc)
        if not expect.get("input_error"):
            result["failures"].append(f"вход неожиданно отклонён: {exc}")
        return result
    if expect.get("input_error"):
        result["status"] = "accepted"
        result["failures"].append("некорректный вход не был отклонён")
        return result

    try:
        card = generate_card(product, client, max_attempts)
    except LLMError as exc:
        result["status"] = "api_error"
        result["failures"].append(f"ошибка API: {exc}")
        return result

    result["status"] = card.status
    result["seconds"] = round(time.perf_counter() - started, 1)
    result["attempts"] = len(card.attempts)
    result["tokens"] = sum(attempt.total_tokens for attempt in card.attempts)
    result["caught"] = Counter(
        issue.code
        for attempt in card.attempts
        for issue in attempt.issues
        if issue.code in FABRICATION_CODES
    )
    result["other_issues"] = Counter(
        issue.code
        for attempt in card.attempts
        for issue in attempt.issues
        if issue.code not in FABRICATION_CODES
    )
    result["final_issues"] = [f"{i.field}: {i.message}" for i in card.issues]
    result["card"] = card.model_dump()

    if "status" in expect and card.status not in expect["status"]:
        result["failures"].append(f"статус {card.status}, ожидался {expect['status']}")
    missing = " ".join(item.field for item in card.missing_fields)
    for name in expect.get("missing", []):
        if name not in missing:
            result["failures"].append(f"не названо недостающее поле: {name}")
    warnings = " ".join(card.warnings)
    for text in expect.get("warning", []):
        if text not in warnings:
            result["failures"].append(f"нет предупреждения: {text}")

    # Независимая проверка: не через валидатор, а поиском запрещённой строки в итоговом тексте
    text = generated_text(card).lower()
    for forbidden in expect.get("must_not_contain", []):
        if forbidden.lower() in text or normalize(forbidden).lower() in normalize(text):
            result["leaks"].append(forbidden)
    return result


def summarize(results: list[dict]) -> dict:
    statuses = Counter(item["status"] for item in results)
    caught = Counter()
    other = Counter()
    for item in results:
        caught.update(item.get("caught", {}))
        other.update(item.get("other_issues", {}))
    generated = [item for item in results if item.get("attempts")]
    seconds = [item["seconds"] / item["attempts"] for item in generated]
    return {
        "cases": len(results),
        "statuses": dict(statuses),
        "checks_passed": sum(1 for item in results if not item["failures"]),
        "cards_generated": len(generated),
        "cases_with_retries": sum(1 for item in generated if item["attempts"] > 1),
        "fabrications_caught": sum(caught.values()),
        "caught_by_type": dict(caught),
        "other_issues": dict(other),
        "leaks_in_final_text": sum(len(item["leaks"]) for item in results),
        "final_cards_with_open_issues": sum(1 for item in results if item.get("final_issues")),
        "seconds_per_attempt": round(sum(seconds) / len(seconds), 1) if seconds else 0,
        "total_seconds": round(sum(item.get("seconds", 0) for item in results), 1),
        "total_tokens": sum(item.get("tokens", 0) for item in results),
    }


def to_markdown(label: str, model: str, summary: dict, results: list[dict]) -> str:
    lines = [
        f"# Eval: {label}",
        "",
        f"Модель: `{model}`. Дата: {date.today().isoformat()}.",
        "",
        "| Показатель | Значение |",
        "|---|---|",
        f"| Случаев | {summary['cases']} |",
        f"| Статусы | {summary['statuses']} |",
        f"| Ожидания сервиса выполнены | {summary['checks_passed']} из {summary['cases']} |",
        f"| Карточек создано моделью | {summary['cards_generated']} |",
        f"| Дошло до повторов | {summary['cases_with_retries']} |",
        f"| Выдумок поймал валидатор (по всем попыткам) | {summary['fabrications_caught']} |",
        f"| По типам | {summary['caught_by_type']} |",
        f"| Прочие ошибки (длина, JSON и др.) | {summary['other_issues']} |",
        f"| Запрещённых строк в итоговых текстах | {summary['leaks_in_final_text']} |",
        f"| Секунд на попытку, в среднем | {summary['seconds_per_attempt']} |",
        f"| Всего секунд | {summary['total_seconds']} |",
        f"| Всего токенов | {summary['total_tokens']} |",
        "",
        "| Случай | Статус | Попыток | Поймано | Открытых проблем | Утечки | Не выполнено |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in results:
        lines.append(
            f"| {item['id']} | {item['status']} | {item.get('attempts', 0)} "
            f"| {sum(item.get('caught', {}).values())} | {len(item.get('final_issues', []))} "
            f"| {', '.join(item['leaks']) or '-'} | {'; '.join(item['failures']) or '-'} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Прогон eval на настоящей модели")
    parser.add_argument("--env-file", help="файл настроек вместо .env")
    parser.add_argument("--label", required=True, help="имя файла с результатом")
    parser.add_argument("--only", help="id одного случая")
    args = parser.parse_args()

    try:
        settings = load_settings(args.env_file)
        settings.check_ready()
    except ConfigError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    client = LLMClient(settings)
    results = []
    for case in CASES:
        if args.only and case["id"] != args.only:
            continue
        result = run_case(case, client, settings.max_attempts)
        results.append(result)
        print(
            f"{result['id']}: {result['status']}, попыток {result.get('attempts', 0)}, "
            f"поймано {sum(result.get('caught', {}).values())}, утечки {result['leaks']}, "
            f"не выполнено {result['failures']}",
            flush=True,
        )

    summary = summarize(results)
    RESULTS_DIR.mkdir(exist_ok=True)
    payload = {
        "label": args.label,
        "model": settings.model,
        "date": date.today().isoformat(),
        "summary": summary,
        "results": results,
    }
    (RESULTS_DIR / f"{args.label}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (RESULTS_DIR / f"{args.label}.md").write_text(
        to_markdown(args.label, settings.model, summary, results), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
