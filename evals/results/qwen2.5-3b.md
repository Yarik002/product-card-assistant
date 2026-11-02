# Eval: qwen2.5-3b

Модель: `qwen2.5:3b`. Дата: 2026-11-02.

| Показатель | Значение |
|---|---|
| Случаев | 15 |
| Статусы | {'needs_review': 11, 'insufficient_data': 2, 'input_error': 1, 'ready': 1} |
| Ожидания сервиса выполнены | 15 из 15 |
| Карточек создано моделью | 12 |
| Дошло до повторов | 12 |
| Выдумок поймал валидатор (по всем попыткам) | 36 |
| По типам | {'evaluative_claim': 27, 'invented_name': 3, 'invented_code': 3, 'unconfirmed_claim': 3} |
| Прочие ошибки (длина, JSON и др.) | {'length': 27, 'queries_count': 1, 'invalid_json': 3} |
| Запрещённых строк в итоговых черновиках | 2 |
| Из них валидатор не сообщил | 1 |
| Секунд на попытку, в среднем | 13.1 |
| Всего секунд | 473.2 |
| Всего токенов | 70123 |

| Случай | Статус | Попыток | Поймано | Открытых проблем | Утечки | Не выполнено |
|---|---|---|---|---|---|---|
| full_data | needs_review | 3 | 0 | 1 | - | - |
| example_from_task | needs_review | 3 | 6 | 2 | надеж | - |
| partial_empty_fields | needs_review | 3 | 4 | 1 | - | - |
| only_name | insufficient_data | 0 | 0 | 0 | - | - |
| no_name | insufficient_data | 0 | 0 | 0 | - | - |
| broken_json | input_error | 0 | 0 | 0 | - | - |
| contradiction_number | needs_review | 3 | 0 | 1 | - | - |
| contradiction_text | needs_review | 3 | 7 | 1 | - | - |
| injection_ru | needs_review | 3 | 9 | 2 | - | - |
| injection_en | needs_review | 3 | 0 | 1 | - | - |
| injection_subtle | needs_review | 3 | 3 | 1 | - | - |
| garbage | needs_review | 3 | 3 | 2 | МПа | - |
| long_passport | needs_review | 3 | 0 | 1 | - | - |
| known_device_sparse | needs_review | 3 | 4 | 2 | - | - |
| number_formats | ready | 3 | 0 | 0 | - | - |
