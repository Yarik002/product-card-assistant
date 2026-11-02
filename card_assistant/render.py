"""Карточка в виде Markdown: удобно скопировать целиком или сохранить в файл."""

from .schemas import Card

STATUS_LABELS = {
    "ready": "готово",
    "needs_review": "нужна проверка",
    "insufficient_data": "мало данных, текст не создан",
}


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- данных нет"]


def card_to_markdown(card: Card) -> str:
    lines = [f"# {card.name or 'Товар без названия'}", ""]
    lines.append(f"**Статус:** {STATUS_LABELS[card.status]}")
    if card.model:
        lines.append(f"**Модель:** {card.model}")
    lines.append("")

    if card.warnings or card.issues:
        lines.append("## Что проверить")
        lines.extend(f"- {warning}" for warning in card.warnings)
        lines.extend(f"- {issue.field}: {issue.message}" for issue in card.issues)
        lines.append("")
    if card.missing_fields:
        lines.append("## Не хватает данных")
        lines.extend(f"- {item.field}: {item.reason}" for item in card.missing_fields)
        lines.append("")

    if card.status != "insufficient_data":
        lines += [f"## SEO-заголовок ({card.seo_title_length} символов)", card.seo_title, ""]
        lines += [
            f"## SEO-описание ({card.seo_description_length} символов)",
            card.seo_description,
            "",
        ]

    lines += ["## Характеристики", "", "| Характеристика | Значение | Источник |", "|---|---|---|"]
    for row in card.characteristics:
        lines.append(f"| {row.name} | {row.value} | {row.source} |")
    lines.append("")

    if card.status != "insufficient_data":
        lines.append("## Поисковые запросы")
        lines.append(card.search_queries_note)
        lines.extend(_bullets(card.search_queries))
        lines += ["", "## Для менеджера", "", "**Кому подходит:**"]
        lines.extend(_bullets(card.commercial.suitable_for))
        lines += ["", "**Какие задачи решает:**"]
        lines.extend(_bullets(card.commercial.tasks))
        if card.commercial.assumptions:
            lines += ["", "**Предположения, проверьте сами:**"]
            lines.extend(f"- {item}" for item in card.commercial.assumptions)
        lines.append("")

    if card.traces:
        lines += ["## Откуда взяты значения", "", "| Значение | Где в тексте | Источник |"]
        lines.append("|---|---|---|")
        lines.extend(f"| {t.value} | {t.used_in} | {t.source} |" for t in card.traces)
        lines.append("")

    return "\n".join(lines)
