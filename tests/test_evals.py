"""Проверяем сам прогон eval на фейковой модели: подсчёты должны быть честными."""

from conftest import MANOMETER, FakeClient, good_draft

from evals.cases import CASES
from evals.run import run_case, summarize


def case(**expect):
    return {"id": "x", "title": "x", "input": MANOMETER, "expect": expect}


def test_case_ids_are_unique_and_set_is_big_enough():
    ids = [item["id"] for item in CASES]
    assert len(ids) == len(set(ids))
    assert 10 <= len(ids) <= 15


def test_leak_is_found_even_if_validator_passed():
    # «DM 02» есть во входе, значит валидатор пропустит, а независимая проверка увидит
    result = run_case(case(must_not_contain=["DM 02"]), FakeClient(good_draft()), 3)
    assert result["status"] == "ready"
    assert result["leaks"] == ["DM 02"]


def test_forbidden_string_is_searched_from_word_start():
    # «бар» находился внутри слова «габаритные», а «МПа» внутри «компанией»
    client = FakeClient(*[good_draft(seo_title="Манометр DM 02, габаритные размеры")] * 3)
    assert run_case(case(must_not_contain=["бар"]), client, 3)["leaks"] == []


def test_caught_fabrications_are_counted_over_attempts():
    bad = good_draft(seo_title="Манометр DM 02 на 2,5 МПа")
    result = run_case(case(status=["ready"]), FakeClient(bad, good_draft()), 3)
    assert result["attempts"] == 2
    assert result["caught"]["invented_number"] == 1
    assert result["failures"] == []
    summary = summarize([result])
    assert summary["fabrications_caught"] == 1
    assert summary["cases_with_retries"] == 1
    assert summary["total_attempts"] == 2


def test_one_very_slow_attempt_does_not_change_median_speed():
    # Так выглядит попытка, во время которой ноутбук ушёл в сон
    attempts = [{"seconds": 10}, {"seconds": 12}, {"seconds": 12000}]
    result = {"status": "ready", "failures": [], "leaks": [], "attempts": 3, "seconds": 12022}
    result["card"] = {"attempts": attempts}
    assert summarize([result])["median_seconds_per_attempt"] == 12


def test_broken_json_case_does_not_call_model():
    client = FakeClient()
    broken = next(item for item in CASES if item["id"] == "broken_json")
    result = run_case(broken, client, 3)
    assert result["status"] == "input_error"
    assert result["failures"] == []
    assert client.calls == []
