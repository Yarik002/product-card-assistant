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
    # Самая частая выдумка без чисел: где прибор применяется и в каких условиях работает
    "отрасли применения": r"отрасл|промышленност|нефтян|нефтегаз|химическ|энергетик|жкх|"
    r"пищев|фармацевт|металлург|судостро",
    "безопасность": r"безопасн",
    # Сама температура не выдумка: термометр её измеряет. Выдумка это условия работы прибора
    "условия эксплуатации": r"вибрац|влажн|агрессивн|коррози|"
    r"температур\w*\s+(?:окружающ|эксплуат|рабоч)|(?:рабоч|высок|повышенн|низк)\w*\s+температур",
}
# Граница слова слева обязательна: «избыточного» содержит «точного»
EVALUATIVE = (
    r"(?<![а-я])(?:самы[йхем]|сам(?:ая|ое|ые|ого|ому)\b|лучш|надеж|высокоточн|"
    r"точн(?:ый|ая|ое|ые|ых|ого|ому|ым)\b|точно\s+(?:опред|измер|показ|контрол)|"
    r"высок\w+\s+точност|обеспеч\w+\s+точност|"
    r"долговечн|качественн|премиальн|уникальн|идеальн|безупречн|непревзойд|превосход|"
    r"исключительн|современн|эффективн|оптимальн|прочн|стабильн|передов|инновацион|"
    r"удобн|прост\w*\s+в\s+(?:использ|эксплуат|монтаж|обслуж))"
)

# Слова, которые встречаются в любом тексте о приборе: опорой на вход они не считаются
STOP_WORDS = {
    "этот", "этого", "этой", "эти", "этих", "также", "может", "могут", "который", "которые",
    "которая", "данный", "данная", "прибор", "прибора", "прибору", "приборы", "приборов",
    "используется", "применяется", "является", "имеет", "обладает", "значение", "значения",
    "характеристики", "характеристик", "характеристика", "покупатель", "покупателю",
    "покупателям", "покупателя", "сравнить", "условия", "условиями", "задачи", "задача",
    "подбор", "подборе", "подбора", "выбор", "выборе", "выбора", "следует", "необходимо", "нужно",
}  # fmt: skip
SENTENCE_MIN_BACKED = 0.4
COMMERCIAL_MIN_BACKED = 0.5

# Параметры, которые легко перепутать. Модель написала «диаметр капилляра 1 000 мм»
# при входе «длина капилляра 1 000 мм»: число есть во входе, но приписано другому параметру
PARAMETER_NOUNS = re.compile(
    r"(?<![а-я])(диаметр|длин|ширин|высот|масс|толщин|глубин|мощност|напряжени)"
)
PLACEHOLDER_RE = re.compile(r"данных нет|нет данных|не указан|без специфическ")


def backed_ratio(text: str, index: InputIndex) -> float:
    """Какая доля значимых слов текста встречается во входе. Это эвристика, а не понимание."""
    words = [
        word
        for word in re.findall(r"[а-я]{4,}", normalize(text).lower())
        if word not in STOP_WORDS
    ]
    if not words:
        return 1.0
    backed = sum(1 for word in words if word[: max(4, len(word) - 3)] in index.full_text)
    return backed / len(words)


def move_unbacked_commercial(draft: LLMDraft, index: InputIndex) -> None:
    """Commercial-блок без опоры на вход код сам переводит в предположения."""
    commercial = draft.commercial
    for name in ("suitable_for", "tasks"):
        kept = []
        for item in getattr(commercial, name):
            if backed_ratio(item, index) < COMMERCIAL_MIN_BACKED:
                commercial.assumptions.append(item)
            else:
                kept.append(item)
        setattr(commercial, name, kept)


def unbacked_sentences(text: str, index: InputIndex) -> list[str]:
    """Предложения, которые стоит прочитать внимательнее. На статус карточки не влияют."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if s and backed_ratio(s, index) < SENTENCE_MIN_BACKED]


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
            issue = issue or _check_binding(fact, normalized, field_name, index)
            if issue:
                issues.append(issue)
            elif located:
                _add_trace(traces, fact.raw, field_name, located)
        issues.extend(_check_names(normalized, field_name, index))
        issues.extend(_check_claims(normalized, field_name, index))
        if PLACEHOLDER_RE.search(normalized.lower()):
            issues.append(
                Issue(
                    code="placeholder",
                    field=field_name,
                    message="не пиши о пробелах в данных, их показывает сервис. Убери это.",
                )
            )
    return issues, traces


def _check_binding(fact, text: str, field_name: str, index: InputIndex) -> Issue | None:
    """Число должно относиться к тому же параметру, что и во входе."""
    if fact.kind != "number":
        return None
    nearby = " ".join(text[: fact.pos].split()[-3:]).lower()
    nouns = PARAMETER_NOUNS.findall(nearby)
    if not nouns or any(nouns[-1] in source for source in index.source_texts_with(fact)):
        return None
    return Issue(
        code="wrong_binding",
        field=field_name,
        value=fact.raw,
        message=f"значение «{fact.raw}» во входе относится не к параметру «{nouns[-1]}». Исправь.",
    )


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
    located = index.locate(fact)
    if located:
        return None, located
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
        # Сравниваем почти целое слово: «точное» не подтверждается «классом точности»
        if not re.search(rf"(?<![а-я]){word[:-2]}[а-я]{{0,3}}(?![а-я])", index.full_text):
            phrase = match.group() if " " in match.group() else word
            issues.append(
                Issue(
                    code="evaluative_claim",
                    field=field_name,
                    value=phrase,
                    message=f"оценка «{phrase}» ничем не подтверждена. Убери её.",
                )
            )
    return issues


def _whole_word(text: str, start: int) -> str:
    return re.match(r"[а-яa-z]+", text[start:]).group()
