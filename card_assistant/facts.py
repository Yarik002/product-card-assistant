"""Извлечение проверяемых фактов из текста: числа с единицами, марки, стандарты, аббревиатуры.

Здесь нет LLM, только регулярные выражения. Один и тот же код разбирает и вход, и ответ модели,
поэтому «1,6 МПа» и «1.6 МПа» превращаются в один и тот же факт.
"""

import re
import unicodedata
from dataclasses import dataclass

# Числа могут стоять рядом с такими единицами. Однобуквенные единицы регистрозависимы:
# «100 В» это вольты, а «100 в корпусе» это предлог.
UNITS = (
    r"(?i:мпа|кпа|гпа|па|бар|мбар|атм|кгс/см2|кгс/см²|мм\s?рт\.?\s?ст\.?|мм\s?вод\.?\s?ст\.?|"
    r"мм|см|км|мкм|кг|мг|мка|ма|ка|квт|вт|ква|кв|мв|гц|кгц|мгц|ом|ком|мом|дб|мин|сек|"
    r"об/мин|м3/ч|м³/ч|л/мин|л/ч|дюйм\w*|°c)"
    r"|%|В|А|м|л|ч"
)
NUMBER_RE = re.compile(rf"(?<![\w.])(\d+(?:\.\d+)?)(?:\s?({UNITS})(?![а-яa-zА-ЯA-Z]))?")
STANDARD_RE = re.compile(
    r"(?<!\w)(ГОСТ(?: Р)?(?: ИСО| МЭК| IEC| EN)?|ТР ТС|ТУ|ОСТ|СТО|ISO|DIN|EN|IEC|ASME|ASTM)"
    r"[ -]?\d[\d.\-/]*\d",
    re.IGNORECASE,
)
# Марки и обозначения: DM 02, G1/2, М20х1,5, RS-485, IP65
CODE_RE = re.compile(
    r"(?<!\w)(?:[A-Za-zА-ЯЁ]{2,8}[ -]?\d|[A-Za-zА-ЯЁ]\d)[\w/.×-]*"
)
LATIN_RE = re.compile(r"(?<![\w-])[A-Za-z][A-Za-z-]+")
ABBR_RE = re.compile(r"(?<!\w)[А-ЯЁ]{2,}(?!\w)")
# Слово с большой буквы не в начале предложения: возможная марка или название
PROPER_RE = re.compile(r"(?<=[а-яa-z0-9,)»] )[А-ЯЁ][а-яё]{2,}")
QUOTED_RE = re.compile(r"«([^»]{2,40})»")
RANGE_GAP_RE = re.compile(r"^\s*(?:-|\.\.\.|до|÷|,|и|/)?\s*[+-]?$")

# Аббревиатуры, которые не являются характеристиками
ALLOWED_ABBR = {"кип", "кипиа"}
# «градусов Цельсия» это запись единицы, а не название компании
ALLOWED_NAMES = {"цельсия"}
# Кириллица, похожая на латиницу: «М20х1,5» и «M20x1.5» это одно и то же
LOOKALIKE = str.maketrans("авекмнорстух", "abekmhopctyx")


def normalize(text: str) -> str:
    """Приводит текст к одному виду: тире, пробелы, десятичная запятая, градусы."""
    text = text.replace("º", "°")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[–—−‒―‑]", "-", text)
    text = text.replace("ё", "е").replace("Ё", "Е")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"°\s?[CСcс](?![а-яa-z])", "°C", text)
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    # Пробелы в больших числах: «1 000» это 1000
    text = re.sub(
        r"(?<![\d.])[1-9]\d{0,2}(?: \d{3})+(?!\d)", lambda m: m.group().replace(" ", ""), text
    )
    # «G 1/2» это G1/2
    text = re.sub(r"(?<![\w])([GM]) (?=\d)", r"\1", text)
    return text


def _canon_number(number: str) -> str:
    if "." in number:
        number = number.rstrip("0").rstrip(".")
    return number


def _canon_code(code: str) -> str:
    return re.sub(r"[\s-]", "", code.rstrip(".-/,")).lower().replace("×", "x").translate(LOOKALIKE)


def _canon_unit(unit: str) -> str:
    return re.sub(r"\s", "", unit).lower().replace("²", "2").replace("³", "3").rstrip(".")


@dataclass(frozen=True)
class Fact:
    kind: str  # number, standard, code, latin, abbr
    key: str
    raw: str
    pos: int
    unit: str = ""


def _blank(text: str, start: int, end: int) -> str:
    """Закрашивает найденное, чтобы цифры из «ГОСТ 2405-88» не считались отдельными числами."""
    return text[:start] + " " * (end - start) + text[end:]


def _numbers(text: str) -> list[Fact]:
    matches = list(NUMBER_RE.finditer(text))
    units = [m.group(2) or "" for m in matches]
    # «0-1.6 МПа» и «от 4 до 20 мА»: единица относится ко всему диапазону
    for i in range(len(matches) - 2, -1, -1):
        gap = text[matches[i].end() : matches[i + 1].start()]
        if not units[i] and units[i + 1] and RANGE_GAP_RE.match(gap):
            units[i] = units[i + 1]

    facts = []
    for match, unit in zip(matches, units, strict=True):
        before = text[: match.start()].rstrip()
        sign = ""
        # Минус считаем знаком, только если перед ним не стоит другое число: «0-1.6» это диапазон
        if before.endswith("-") and not before[:-1].rstrip()[-1:].isdigit():
            sign = "-"
        facts.append(
            Fact(
                kind="number",
                key=sign + _canon_number(match.group(1)),
                raw=match.group().strip(),
                pos=match.start(),
                unit=_canon_unit(unit),
            )
        )
    return facts


def extract_facts(text: str) -> list[Fact]:
    """Находит факты в уже нормализованном тексте."""
    facts = []
    working = text

    for match in STANDARD_RE.finditer(working):
        facts.append(
            Fact("standard", _canon_code(match.group()), match.group(), match.start())
        )
        working = _blank(working, match.start(), match.end())

    for match in list(CODE_RE.finditer(working)):
        raw = match.group().rstrip(".-/,")
        facts.append(Fact("code", _canon_code(raw), raw, match.start()))
        working = _blank(working, match.start(), match.end())

    facts.extend(_numbers(working))

    for match in LATIN_RE.finditer(working):
        word = match.group().strip("-")
        facts.append(Fact("latin", word.lower(), word, match.start()))

    for match in ABBR_RE.finditer(working):
        if match.group().lower() not in ALLOWED_ABBR:
            facts.append(Fact("abbr", match.group().lower(), match.group(), match.start()))

    return sorted(facts, key=lambda fact: fact.pos)


def word_stem(word: str) -> str:
    """Грубая основа слова: падежи не должны давать ложных срабатываний."""
    word = word.lower()
    return word[: max(3, len(word) - 2)]


def proper_names(text: str) -> list[str]:
    """Слова с большой буквы внутри предложения и названия в кавычках."""
    names = PROPER_RE.findall(text)
    names.extend(quoted.split()[0] for quoted in QUOTED_RE.findall(text))
    return [name for name in names if name.lower() not in ALLOWED_NAMES]


@dataclass(frozen=True)
class Located:
    source: str
    snippet: str


class InputIndex:
    """Всё, что есть во входных данных, с указанием поля-источника."""

    def __init__(self, sources: dict[str, str]):
        self.sources = []
        for label, text in sources.items():
            normalized = normalize(text)
            self.sources.append((label, normalized, extract_facts(normalized)))
        self.full_text = " ".join(text for _, text, _ in self.sources).lower()

    def locate(self, fact: Fact) -> Located | None:
        """Ищет факт во входе. Единица должна совпасть, если она указана в тексте модели."""
        for label, text, facts in self.sources:
            for known in facts:
                if self._same(fact, known):
                    return Located(label, _snippet(text, known))
        # Часть марки: «DM» из «DM 02» или код целиком, написанный слитно
        if fact.kind in ("latin", "code", "abbr") and self._in_codes(fact):
            return self._first_source_with(fact)
        return None

    def source_texts_with(self, fact: Fact) -> list[str]:
        """Тексты всех полей входа, где встречается этот факт."""
        return [
            text.lower()
            for _, text, facts in self.sources
            if any(self._same(fact, known) for known in facts)
        ]

    def number_known(self, key: str) -> bool:
        return any(
            known.kind == "number" and known.key == key
            for _, _, facts in self.sources
            for known in facts
        )

    def has_stem(self, word: str) -> bool:
        return word_stem(normalize(word)) in self.full_text

    def _in_codes(self, fact: Fact) -> bool:
        return any(
            known.kind in ("code", "standard") and _code_part(fact.key, known.key)
            for _, _, facts in self.sources
            for known in facts
        )

    def _first_source_with(self, fact: Fact) -> Located | None:
        for label, text, facts in self.sources:
            for known in facts:
                if known.kind in ("code", "standard") and _code_part(fact.key, known.key):
                    return Located(label, _snippet(text, known))
        return None

    @staticmethod
    def _same(fact: Fact, known: Fact) -> bool:
        if fact.kind != known.kind and {fact.kind, known.kind} != {"code", "abbr"}:
            return False
        if fact.key != known.key and _canon_code(fact.key) != _canon_code(known.key):
            return False
        return fact.kind != "number" or not fact.unit or fact.unit == known.unit


def _code_part(part: str, code: str) -> bool:
    """«dm» это начало кода «dm02»: буквенная часть марки без номера допустима."""
    return re.fullmatch(r"[a-zа-я]+", part) is not None and code.startswith(_canon_code(part))


def _snippet(text: str, fact: Fact, radius: int = 35) -> str:
    start = max(0, fact.pos - radius)
    end = min(len(text), fact.pos + len(fact.raw) + radius)
    return ("..." if start else "") + text[start:end].strip() + ("..." if end < len(text) else "")
