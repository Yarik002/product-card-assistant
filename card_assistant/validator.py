"""Проверка ответа модели кодом: длины и сверка каждого факта со входом."""

import re

from .facts import InputIndex, Located, extract_facts, normalize, proper_names
from .precheck import Contradiction
from .schemas import FactTrace, Issue, LLMDraft

TITLE_MAX = 70
DESCRIPTION_MIN = 800
DESCRIPTION_MAX = 1200
QUERIES_MIN = 3
QUERIES_MAX = 5

# Без данных нельзя утверждать. Срабатывает, только если основы слова нет во входе
UNCONFIRMED_TOPICS = {
    "поверка": r"поверк|поверен|поверочн",
    "Госреестр СИ": r"госреестр|реестр\w*\s+си(?!\w)|реестр\w*\s+средств",
    "межповерочный интервал": r"межповерочн|(?<!\w)мпи(?!\w)",
    "взрывозащита": r"взрывозащищ|взрывозащит|взрывобезопас|(?<!\w)ex\s?[di](?!\w)",
    "степень защиты IP": r"(?<!\w)ip\s?\d|степен\w*\s+защит|пыле|влагозащит|герметичн",
    "гарантия": r"гаранти",
    "страна производства": r"страна|российск|отечественн|импортн|зарубежн|произведен\w*\s+в(?!\w)",
    "сертификат": r"сертифик|декларац\w*\s+соответ",
    "питание": r"питани",
    "интерфейсы": r"интерфейс|протокол",
    "класс точности": r"класс\w*\s+точност",
    "диапазон измерения": r"диапазон\w*\s+измер",
    "тип корпуса": r"тип\w*\s+корпус",
}
EVALUATIVE = (
    r"самы[йхем]|сам(?:ая|ое|ые|ого|ому)\b|лучш|надежн|высокоточн|точн(?:ый|ая|ое|ые|ых|ого|ому|ым)\b|"
    r"высок\w+\s+точност|долговечн|качественн|премиальн|уникальн|идеальн|безупречн|"
    r"непревзойд|превосход|исключительн|современн|эффективн|оптимальн|прочн|стабильн|"
    r"передов|инновацион"
)


def _fields(draft: LLMDraft) -> list[tuple[str, str]]:
    fields = [("SEO-заголовок", draft.seo_title), ("SEO-описание", draft.seo_description)]
    fields += [(f"запрос {i}", q) for i, q in enumerate(draft.search_queries, 1)]
    commercial = draft.commercial
    fields += [(f"кому подходит {i}", s) for i, s in enumerate(commercial.suitable_for, 1)]
    fields += [(f"задача {i}", s) for i, s in enumerate(commercial.tasks, 1)]
    fields += [(f"предположение {i}", s) for i, s in enumerate(commercial.assumptions, 1)]
    return fields


def check_structure(draft: LLMDraft) -> list[Issue]:
    issues = []
    title_len = len(draft.seo_title)
    if not draft.seo_title.strip():
        issues.append(Issue(code="empty", field="SEO-заголовок", message="заголовок пустой."))
    elif title_len > TITLE_MAX:
        issues.append(
            Issue(
                code="length",
                field="SEO-заголовок",
                message=f"сейчас {title_len} символов, нужно не больше {TITLE_MAX}. "
                f"Сократи минимум на {title_len - TITLE_MAX}.",
            )
        )
    desc_len = len(draft.seo_description)
    if desc_len < DESCRIPTION_MIN:
        issues.append(
            Issue(
                code="length",
                field="SEO-описание",
                message=f"сейчас {desc_len} символов, нужно от {DESCRIPTION_MIN} до "
                f"{DESCRIPTION_MAX}. Добавь минимум {DESCRIPTION_MIN - desc_len} символов "
                "без новых фактов.",
            )
        )
    elif desc_len > DESCRIPTION_MAX:
        issues.append(
            Issue(
                code="length",
                field="SEO-описание",
                message=f"сейчас {desc_len} символов, нужно от {DESCRIPTION_MIN} до "
                f"{DESCRIPTION_MAX}. Сократи минимум на {desc_len - DESCRIPTION_MAX}.",
            )
        )
    count = len([q for q in draft.search_queries if q.strip()])
    if not QUERIES_MIN <= count <= QUERIES_MAX:
        issues.append(
            Issue(
                code="queries_count",
                field="поисковые запросы",
                message=f"сейчас {count}, нужно от {QUERIES_MIN} до {QUERIES_MAX}.",
            )
        )
    if not draft.commercial.suitable_for or not draft.commercial.tasks:
        issues.append(
            Issue(
                code="empty",
                field="commercial-блок",
                message="заполни suitable_for и tasks, опираясь на входные данные.",
            )
        )
    return issues


def check_facts(
    draft: LLMDraft, index: InputIndex, contradictions: list[Contradiction]
) -> tuple[list[Issue], list[FactTrace]]:
    """Каждое число, марка и стандарт из текста модели должны найтись во входе."""
    issues: list[Issue] = []
    traces: list[FactTrace] = []
    conflict_keys = {key for item in contradictions for key in item.keys}

    for field_name, text in _fields(draft):
        normalized = normalize(text)
        seen = set()
        for fact in extract_facts(normalized):
            ident = (fact.kind, fact.key, fact.unit)
            if ident in seen:
                continue
            seen.add(ident)
            issue, located = _check_fact(fact, field_name, index, conflict_keys)
            if issue:
                issues.append(issue)
            elif located:
                _add_trace(traces, fact.raw, field_name, located)
        issues.extend(_check_names(normalized, field_name, index))
        issues.extend(_check_claims(normalized, field_name, index))
        if "данных нет" in normalized.lower() or "нет данных" in normalized.lower():
            issues.append(
                Issue(
                    code="placeholder",
                    field=field_name,
                    message="не пиши в тексте «данных нет», пробелы показывает сервис. Убери это.",
                )
            )
    return issues, traces


def _add_trace(traces: list[FactTrace], raw: str, field_name: str, located: Located) -> None:
    """Одно значение из одного источника показываем одной строкой."""
    value = re.sub(r"(?<=\d)\.(?=\d)", ",", raw)  # контент-менеджеру привычна запятая
    for trace in traces:
        if trace.value == value and trace.source == located.source:
            trace.used_in += f", {field_name}"
            return
    traces.append(
        FactTrace(value=value, used_in=field_name, source=located.source, snippet=located.snippet)
    )


def _check_fact(fact, field_name, index, conflict_keys) -> tuple[Issue | None, Located | None]:
    if fact.key in conflict_keys:
        return (
            Issue(
                code="conflicting_value",
                field=field_name,
                value=fact.raw,
                message=f"значение «{fact.raw}» относится к полю с противоречием. Убери его.",
            ),
            None,
        )
    located = index.locate(fact)
    if located:
        return None, located
    if fact.kind == "number" and index.number_known(fact.key):
        return (
            Issue(
                code="invented_unit",
                field=field_name,
                value=fact.raw,
                message=f"число есть во входе, но с другой единицей: «{fact.raw}». "
                "Пиши единицу как во входе или убери значение.",
            ),
            None,
        )
    code = {
        "number": "invented_number",
        "standard": "invented_standard",
        "code": "invented_code",
        "latin": "invented_name",
        "abbr": "invented_name",
    }[fact.kind]
    return (
        Issue(
            code=code,
            field=field_name,
            value=fact.raw,
            message=f"значения «{fact.raw}» нет во входных данных. Убери его.",
        ),
        None,
    )


def _check_names(text: str, field_name: str, index: InputIndex) -> list[Issue]:
    return [
        Issue(
            code="invented_name",
            field=field_name,
            value=name,
            message=f"названия «{name}» нет во входных данных. Убери его.",
        )
        for name in proper_names(text)
        if not index.has_stem(name)
    ]


def _check_claims(text: str, field_name: str, index: InputIndex) -> list[Issue]:
    issues = []
    lowered = text.lower()
    # В предположениях менеджер и так проверит каждое слово, темы там допустимы, оценки нет
    if not field_name.startswith("предположение"):
        for topic, pattern in UNCONFIRMED_TOPICS.items():
            match = re.search(pattern, lowered)
            if match and not re.search(pattern, index.full_text):
                issues.append(
                    Issue(
                        code="unconfirmed_claim",
                        field=field_name,
                        value=match.group(),
                        message=f"во входе нет данных о теме «{topic}». Убери упоминание.",
                    )
                )
    for match in re.finditer(EVALUATIVE, lowered):
        word = _whole_word(lowered, match.start())
        if word[:5] not in index.full_text:
            issues.append(
                Issue(
                    code="evaluative_claim",
                    field=field_name,
                    value=word,
                    message=f"оценка «{word}» ничем не подтверждена. Убери её.",
                )
            )
    return issues


def _whole_word(text: str, start: int) -> str:
    return re.match(r"[а-яa-z]+", text[start:]).group()
