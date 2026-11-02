import pytest

from card_assistant.facts import InputIndex, extract_facts, normalize


def keys(text, kind):
    return [f.key for f in extract_facts(normalize(text)) if f.kind == kind]


def number_units(text):
    return [(f.key, f.unit) for f in extract_facts(normalize(text)) if f.kind == "number"]


@pytest.mark.parametrize(
    "variant",
    ["1,6 МПа", "1.6 МПа", "1,6 МПа", "1,60 МПа", "1.6МПа", "1,6 мпа"],
)
def test_number_normalization(variant):
    assert number_units(variant) == [("1.6", "мпа")]


@pytest.mark.parametrize("variant", ["0–1,6 МПа", "0-1.6 МПа", "0—1,6 МПа", "от 0 до 1,6 МПа"])
def test_range_gives_unit_to_both_numbers(variant):
    assert number_units(variant) == [("0", "мпа"), ("1.6", "мпа")]


def test_spaces_in_big_numbers():
    assert number_units("1 000 мм") == [("1000", "мм")]
    assert number_units("10 000 Па") == [("10000", "па")]


def test_neighbouring_values_are_not_glued_into_big_number():
    # Модель пишет «G1/2 100 мм», а правило про пробелы в числах делало из этого G1/2100
    assert keys("G1/2 100 мм", "code") == ["g1/2"]
    assert number_units("G1/2 100 мм") == [("100", "мм")]
    assert number_units("М20 100 мм") == [("100", "мм")]


def test_lowercase_code_in_search_query_is_found():
    # Ложная ошибка заставила модель убрать правильную марку: «ТМ-5» стал «ТМ»
    index = InputIndex({"name": "Термометр ТМ-5", "x": "М20х1,5", "y": "Манометр DM 02"})
    for text in ("тм-5", "м20х1,5", "dm 02"):
        facts = extract_facts(normalize(text))
        assert facts and all(index.locate(fact) for fact in facts), text


def test_lowercase_word_before_number_is_not_a_code():
    assert number_units("до 5 МПа") == [("5", "мпа")]
    assert number_units("при 100 мм") == [("100", "мм")]


def test_minus_is_sign_only_outside_range():
    assert number_units("от -40 до +60 °С") == [("-40", "°c"), ("60", "°c")]
    assert number_units("−40…+60 ºC") == [("-40", "°c"), ("60", "°c")]


def test_preposition_is_not_a_unit():
    assert number_units("100 в корпусе") == [("100", "")]
    assert number_units("24 В") == [("24", "в")]


def test_standard_is_one_fact():
    text = "по ГОСТ 2405-88"
    assert len(keys(text, "standard")) == 1
    assert keys(text, "standard") == keys("ГОСТ 2405–88", "standard")
    assert keys(text, "standard") != keys("ГОСТ 2405-89", "standard")
    assert keys(text, "number") == []


def test_codes_match_with_lookalike_letters_and_spaces():
    index = InputIndex({"specs.резьба": "М20х1,5", "name": "Манометр DM 02", "x": "G1/2"})
    for text in ("M20x1.5", "DM 02", "DM02", "G 1/2", "DM"):
        for fact in extract_facts(normalize(text)):
            assert index.locate(fact) is not None, text


def test_unknown_code_is_not_found():
    index = InputIndex({"name": "Манометр DM 02"})
    for text in ("DM 03", "RS-485", "IP65", "ГОСТ 2405-88", "Modbus"):
        for fact in extract_facts(normalize(text)):
            assert index.locate(fact) is None, text


def test_locate_reports_source_field():
    index = InputIndex({"specs.диапазон": "0–1,6 МПа", "description": "давление до 10 бар"})
    fact = next(f for f in extract_facts(normalize("1.6 МПа")) if f.kind == "number")
    assert index.locate(fact).source == "specs.диапазон"
    fact = next(f for f in extract_facts(normalize("10 бар")) if f.kind == "number")
    assert index.locate(fact).source == "description"
    assert "10 бар" in index.locate(fact).snippet


def test_number_with_other_unit_is_not_found():
    index = InputIndex({"specs.диапазон": "0–1,6 МПа"})
    fact = next(f for f in extract_facts(normalize("1,6 бар")) if f.kind == "number")
    assert index.locate(fact) is None
    assert index.number_known("1.6")
